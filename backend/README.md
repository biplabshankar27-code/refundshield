# RefundShield Backend

Defense-only AI risk API. Python 3.11+, FastAPI, SQLite.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # fill in RAZORPAY_KEY_ID / KEY_SECRET (TEST MODE)
```

`.env` is gitignored. Credentials are read **only** from environment
variables via pydantic-settings — never hardcoded. The app refuses
`rzp_live_*` keys twice: once in `Settings`, again in `RazorpayTestClient`.

## Run

```bash
python -m uvicorn app.main:app --reload --port 8000
```

## Test

```bash
python -m pytest tests -q
```

## Modules

| Path | Role |
|------|------|
| `app/config.py` | pydantic-settings; test-mode enforcement |
| `app/razorpay_client.py` | Official SDK wrapper (Test Mode only) |
| `app/core/models.py` | Domain models (Stage 1, Stage 2, Razorpay, audit) |
| `app/core/db.py` | SQLite (WAL) + schema |
| `app/core/audit.py` | Append-only audit trail |
| `app/data/generator.py` | Seeded synthetic populations + evidence images |
| `app/data/images.py` | Deterministic PNG evidence factory |
| `app/data/razorpay_sync.py` | Pull / push / enrich Test-Mode orders |
| `app/data/webhooks.py` | HMAC webhook builder/verifier |
| `app/stage1/*` | Image, history, text, payment/delivery → scorer → orchestrator |
| `app/stage2/*` | Graph → Louvain → ring score → temporal → counterfactual |
| `app/evaluation/metrics.py` | Honest metrics (ground truth never a signal) |
| `app/routers/*` | API surface |

## Stage 1 weights (fixed & explainable)

| Signal | Weight |
|--------|--------|
| image_evidence | 0.30 |
| history_evidence | 0.20 |
| payment_delivery_evidence | 0.30 |
| text_evidence | 0.20 |

Bands: `≥0.85 critical · ≥0.60 high · ≥0.35 medium · else low`.
Actions (defense-only): `approve_normally | manual_review | manual_review_urgent`.

## Ring score

`ring_score = 0.6 × avg_stage1_risk + 0.4 × graph_density` (strict).
Temporal coordination (burst / staggered / regular-spacing) feeds
adversarial flags and the narrative, never the formula.
