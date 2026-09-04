"""RefundShield on Modal — serverless deployment of the FastAPI backend.

One command deploys the whole backend with data pre-seeded at build time:

    cd backend
    pip install modal
    modal setup                        # one-time auth
    modal secret create refundshield-secrets \\
        RAZORPAY_KEY_ID=rzp_test_xxxx \\
        RAZORPAY_KEY_SECRET=xxxx \\
        CORS_ORIGINS=https://your-frontend.vercel.app
    modal deploy modal_app.py

Design:
- Image build runs ``prepare_seed`` once: generates the synthetic dataset,
  runs Stage 1 + Stage 2, and bakes ``/app/seed/refundshield.db`` into the
  image layer — so the deployed API is instantly populated.
- A Modal Volume at ``/data`` persists runtime writes (new claims, new
  detection runs, audit events). On cold start the baked seed DB is copied
  to the volume only if the volume is empty.
- ``max_containers=1`` keeps a single writer for SQLite and avoids
  duplicate cold starts.
- Razorpay keys come ONLY from the Modal secret — never from code.
"""

import modal

app = modal.App("refundshield")

volume = modal.Volume.from_name("refundshield-data", create_if_missing=True)

secrets = [modal.Secret.from_name("refundshield-secrets")]


def prepare_seed():
    """Build-time step: generate + analyze + detect, baking a ready DB.

    Runs inside the image build with all dependencies installed. The
    resulting /app/seed/refundshield.db ships inside the image so the API
    has data on its very first request.
    """
    import os

    from app.core.audit import AuditTrail
    from app.core.db import Database
    from app.data.generator import (
        DatasetGenerator,
        GeneratorConfig,
        load_claims,
        load_orders,
    )
    from app.stage1.claim_analyzer import ClaimAnalyzer, build_claim_input
    from app.stage2.ring_detection import RingDetectionService

    seed_db = "/app/seed/refundshield.db"
    os.makedirs("/app/seed", exist_ok=True)

    db = Database(seed_db)
    DatasetGenerator(
        db,
        GeneratorConfig(
            seed=42,
            n_normal=14,
            n_fraudsters=4,
            n_rings=2,
            ring_size=4,
            n_adversarial_rings=1,
            adversarial_ring_size=4,
            image_dir="/app/seed/synthetic_images",
        ),
    ).generate()

    audit = AuditTrail(db)
    analyzer = ClaimAnalyzer(db, audit, enable_razorpay=False)
    orders = {o["order_id"]: o for o in load_orders(db)}
    for row in load_claims(db):
        analyzer.analyze(build_claim_input(row, orders.get(row["order_id"])))

    result = RingDetectionService(db, audit).run()
    print(
        f"[seed] {len(load_claims(db))} claims analyzed, "
        f"{len(result.rings)} rings detected"
    )


image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("requirements.txt")
    # copy=True bakes code + the seeded DB into the image layer
    .add_local_dir("app", remote_path="/app/app", copy=True)
    .add_local_file("requirements.txt", remote_path="/app/requirements.txt", copy=True)
    .workdir("/app")
    .run_function(prepare_seed)
)


@app.function(
    image=image,
    secrets=secrets,
    volumes={"/data": volume},
    cpu=1.0,
    memory=1024,
    scaledown_window=600,   # stay warm 10 min after last request (cheap)
    max_containers=1,       # single SQLite writer + no duplicate cold starts
)
@modal.asgi_app()
def api():
    """Serve the FastAPI app; runs on each container cold start."""
    import os
    import shutil

    # --- runtime defaults (Secrets may override RAZORPAY_* / CORS) ------
    os.environ.setdefault("DATABASE_URL", "sqlite:////data/refundshield.db")
    os.environ.setdefault("REFUNDSHIELD_IMAGE_DIR", "/data/synthetic_images")
    os.environ.setdefault("REFUNDSHIELD_ENV", "production")

    # --- seed the persistent volume once --------------------------------
    os.makedirs("/data", exist_ok=True)
    if not os.path.exists("/data/refundshield.db"):
        shutil.copy("/app/seed/refundshield.db", "/data/refundshield.db")
        print("[modal] volume seeded from baked image data")
    volume.commit()

    from app.main import app as fastapi_app

    return fastapi_app
