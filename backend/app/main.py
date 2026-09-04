"""RefundShield API entrypoint.

Defense-only guarantee: this service NEVER blocks accounts, cancels
payments, or takes enforcement actions. It only scores, flags, explains,
and logs.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app.core.deps import get_db
from app.routers import audit, claims, demo, evaluation, rings, webhooks


def _configure_logging() -> None:
    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger("refundshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    logger.info(
        "RefundShield ready — db=%s, razorpay=%s (TEST MODE only)",
        db.path,
        "configured" if get_settings().credentials_configured else "not configured",
    )
    yield
    logger.info("RefundShield shutting down")


app = FastAPI(
    title="RefundShield API",
    version=__version__,
    lifespan=lifespan,
    description=(
        "Two-stage, defense-only AI risk system: Stage 1 individual claim "
        "intelligence, Stage 2 abuse-ring detection. Razorpay Test Mode only."
    ),
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["http://127.0.0.1:3000"],
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (claims.router, rings.router, audit.router,
               evaluation.router, demo.router, webhooks.router):
    app.include_router(router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/")
def root() -> dict:
    return {
        "service": "RefundShield",
        "version": __version__,
        "mode": "razorpay-test-only",
        "defense_only": True,
        "endpoints": [
            "POST /api/claims/analyze",
            "GET  /api/claims/results",
            "GET  /api/claims/{claim_id}",
            "POST /api/rings/detect",
            "GET  /api/rings/latest",
            "GET  /api/audit",
            "GET  /api/evaluation/metrics",
            "POST /api/demo/bootstrap",
            "GET  /api/demo/cost-of-delay",
            "POST /api/demo/simulate-webhook",
            "POST /api/webhooks/razorpay",
        ],
    }


@app.get("/health")
def health() -> dict:
    db = get_db()
    return {"status": "ok", "database": "ok" if db.path else "missing"}
