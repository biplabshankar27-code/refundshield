# RefundShield

**Two-stage, defense-only AI risk system for refund & return abuse.**
Built for the Razorpay AI Buildathon 2026 — Track 02 · AI Risk Manager.

RefundShield detects (1) individual refund/return fraud and (2) organized
abuse rings, explains every decision in plain English, and simulates the
cost of delayed review in ₹. It is **defense-only**: it scores, flags,
explains, and logs — it never blocks accounts or takes enforcement action.

---

## Architecture

```
                      ┌────────────────────────────────────────────┐
                      │              3D Story Frontend             │
                      │  Next.js 15 · React Three Fiber · Zustand  │
                      │  6 narrative chapters over a shared Canvas │
                      └──────────────────┬─────────────────────────┘
                                         │ REST (localhost:8000)
┌────────────────────────────────────────┴─────────────────────────────────┐
│                            FastAPI Backend                               │
│                                                                          │
│  Stage 1 · Claim Intelligence        Stage 2 · Ring Detection            │
│  ├─ image_analyzer   (pHash + AI)    ├─ graph_builder (device/addr/      │
│  ├─ history_analyzer                   VPA/image-pHash edges)            │
│  ├─ text_analyzer                    ├─ community_detection (Louvain)    │
│  ├─ payment_delivery_signals         ├─ ring_scorer                      │
│  │                                   │   ring = 0.6·avg_risk             │
│  ├─ scorer (weights .30/.20/.30/.20) │          + 0.4·density            │
│  └─ claim_analyzer                   ├─ temporal_detection (burst /      │
│                                        staggered / adversarial)          │
│  core/                               ├─ counterfactual (₹ cost-of-delay) │
│  ├─ models.py (pydantic)             └─ ring_detection (orchestrator)    │
│  ├─ db.py  · audit.py (SQLite WAL)                                       │
│  └─ deps.py                          evaluation/ (honest metrics)        │
│                                                                          │
│  data/ (synthetic generator + evidence images)                           │
│  razorpay_client.py → Razorpay SDK · TEST MODE ONLY                      │
│  data/razorpay_sync.py → pull / push / enrich Test-Mode orders           │
└──────────────────────────────────────────────────────────────────────────┘
```

**Ring score (strict):** `ring_score = 0.6 × avg_stage1_risk + 0.4 × graph_density`
— temporal coordination informs adversarial flags but never the formula.

**Defense-only:** the action ladder is `approve_normally → manual_review →
manual_review_urgent`. There is no block state anywhere in the codebase
(enforced by tests).

## Quickstart

### 1 · Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env                 # then paste your TEST keys into .env
python -m uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- Keys load **only** from environment / `.env` (pydantic-settings). Live
  keys (`rzp_live_…`) are rejected at config *and* client level.

### 2 · Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` if the backend is not on `localhost:8000`.

### 3 · One-shot demo data

Either press **“Run demo pipeline”** in the UI, or:

```bash
curl -X POST http://localhost:8000/api/demo/bootstrap \
  -H "Content-Type: application/json" -d '{}'
```

This generates a seeded synthetic dataset (honest buyers, individual
fraudsters, coordinated rings, evasion-trained adversarial rings),
runs Stage 1 over every claim, runs Stage 2 ring detection, and stores
results + audit events.

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/claims/analyze` | Stage 1: score one refund/return claim |
| GET  | `/api/claims/results` | Stored Stage 1 results (latest first) |
| GET  | `/api/claims/{claim_id}` | Full result for one claim |
| POST | `/api/rings/detect` | Stage 2: full detection run |
| GET  | `/api/rings/latest` | Most recent stored run |
| GET  | `/api/audit` | Append-only audit trail (filterable) |
| GET  | `/api/evaluation/metrics` | Honest precision/recall/AUC + ring metrics |
| POST | `/api/demo/bootstrap` | Generate data + run both stages |
| GET  | `/api/demo/cost-of-delay` | ₹ exposure scenarios (7/14/30 days) |
| POST | `/api/demo/simulate-webhook` | Sign + verify a Razorpay-shaped webhook |
| POST | `/api/webhooks/razorpay` | Signature-verified webhook receiver |

## Razorpay Test Mode integration

- `razorpay_client.py` wraps the official SDK; refuses non-`rzp_test_` keys.
- Sync service pulls Test orders/payments into a local mirror, can push
  generated orders via `order.create`, and enriches claims with payment
  facts (method, capture status, amounts).
- Webhook payloads are HMAC-SHA256 verified exactly as production Razorpay
  webhooks are. All money actions stay in Test Mode.

## Honest evaluation

Ground-truth labels exist only inside the synthetic dataset and are never
visible to any scorer (enforced by tests). `/api/evaluation/metrics`
reports claim-level precision/recall/F1/AUC at a chosen threshold and
member-level ring precision/recall against the planted rings.

## Design system

Six tokens only: `background #0B0F14 · surface #151C26 · primary #4C8DFF ·
accent #8AE0B0 · danger #FF6B6B · text #E8EEF6`. Danger is reserved for
risk; accent for verification/trust. No two high-saturation colours are
ever stacked; overlays sit on blurred surface panels with generous space.

## Repository layout

```
backend/    FastAPI app · stage1/ · stage2/ · core/ · data/ · evaluation/ · tests/
frontend/   Next.js app · components/{canvas,story,ui} · lib/
.env files  backend/.env (gitignored) · backend/.env.example (template)
```

## Running tests

```bash
cd backend && .venv/Scripts/python -m pytest tests -q   # 113 tests
cd frontend && npm run build                            # type-checked build
```
