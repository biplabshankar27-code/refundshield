<div align="center">

# 🛡 RefundShield

**Two-stage, defense-only AI risk system for refund & return abuse.**

Detect individual claim fraud · Uncover organized abuse rings · Explain every
decision in plain English · Simulate the cost of delayed review in ₹

*Razorpay AI Buildathon 2026 — Track 02 · AI Risk Manager*

[![Live Demo](https://img.shields.io/badge/demo-frontend_biplab.vercel.app-4C8DFF)](https://frontend-biplab.vercel.app/)
[![API](https://img.shields.io/badge/API-Modal_(Test_Mode)-8AE0B0)](https://biplabshankar27-code--refundshield-api.modal.run/docs)
[![Tests](https://img.shields.io/badge/tests-113%20passing-8AE0B0)](#testing)
[![Python](https://img.shields.io/badge/python-3.12-E8EEF6)](#)
[![Next.js](https://img.shields.io/badge/next.js-15-E8EEF6)](#)

[Live Demo](https://frontend-biplab.vercel.app/) ·
[API Docs (Swagger)](https://biplabshankar27-code--refundshield-api.modal.run/docs) ·
[Deployment Guide](DEPLOY.md)

</div>

---

## Live demo

| Piece | URL |
|---|---|
| 🎬 3D story frontend | **https://frontend-biplab.vercel.app** |
| ⚙️ FastAPI backend | https://biplabshankar27-code--refundshield-api.modal.run |
| 📚 Swagger / OpenAPI | https://biplabshankar27-code--refundshield-api.modal.run/docs |

The deployed backend is pre-seeded at build time (synthetic dataset → Stage 1 →
Stage 2), so the story is populated on first visit. Press **“Run demo
pipeline”** in the UI to generate a larger live dataset.

## What RefundShield does

Merchants lose money to refund abuse twice: once to individual fraudulent
claims, and again to *organized rings* that share devices, addresses, bank
accounts and even the same evidence photos. RefundShield detects both — and
never takes enforcement action.

**Defense-only guarantee.** The system scores, flags, explains and logs. The
action ladder is `approve_normally → manual_review → manual_review_urgent`.
There is no “block” state anywhere in the codebase — enforced by tests.

### Stage 1 — Individual Claim Intelligence

Four independent, explainable signals score each refund/return request:

| Signal | Weight | What it checks |
|---|---|---|
| Image evidence | 0.30 | Reuse vs. prior claims (perceptual hash), AI-generation artefacts (checkerboard banding + mirror symmetry), missing EXIF |
| Customer history | 0.20 | Account age, refund ratio, chargebacks, order velocity |
| Payment & delivery | 0.30 | Claimed vs. paid amount, claim-before-delivery, reflex claims, address changes, capture status (Razorpay Test Mode) |
| Claim text | 0.20 | Urgency, threats/escalation, negativity, vagueness |

Output: risk score 0–1, band (`low/medium/high/critical`), review priority,
plain-English reason, and a defense-only recommended action.

### Stage 2 — Abuse Ring Detection

Customers become a graph (edges: shared device, address, refund VPA,
identical evidence pHash). Louvain communities are split into connected
components, then scored with the **strict formula**:

```
ring_score = 0.6 × avg_stage1_risk + 0.4 × graph_density
```

Temporal analysis separates **burst rings** (claims within 72 h) from
**adversarial rings** (staggered, evasion-aware timing) — coordination feeds
explanatory flags, never the formula. A counterfactual simulation projects
**cost of delay in ₹** over 7 / 14 / 30 days. Every run is written to an
append-only audit trail.

## Architecture

```
                ┌───────────────────────────────────────┐
                │      3D Story Frontend (Vercel)       │
                │  Next.js 15 · R3F · Zustand · Motion  │
                │  6 narrative chapters over one Canvas │
                └──────────────────┬────────────────────┘
                                   │ REST
┌──────────────────────────────────┴─────────────────────────────────┐
│                       FastAPI Backend (Modal)                      │
│                                                                    │
│  Stage 1                          Stage 2                          │
│  ├─ image_analyzer                ├─ graph_builder                 │
│  ├─ history_analyzer              ├─ community_detection (Louvain) │
│  ├─ text_analyzer                 ├─ ring_scorer (strict formula)  │
│  ├─ payment_delivery_signals      ├─ temporal_detection            │
│  ├─ scorer (fixed weights)        ├─ counterfactual (₹)            │
│  └─ claim_analyzer                └─ ring_detection                │
│                                                                    │
│  core/ models · SQLite(WAL) audit trail · deps                     │
│  data/ synthetic generator · evidence images · Razorpay sync       │
│  razorpay_client.py → official SDK, TEST MODE ONLY                 │
│  evaluation/ honest metrics (ground truth never a signal)          │
└────────────────────────────────────────────────────────────────────┘
```

## Quickstart

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                # paste your Razorpay TEST keys
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 18+):

```bash
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

**Demo data:** press “Run demo pipeline” in the UI, or:

```bash
curl -X POST http://localhost:8000/api/demo/bootstrap -H "Content-Type: application/json" -d '{}'
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/claims/analyze` | Stage 1: score one claim |
| GET | `/api/claims/results` | Stored Stage 1 results |
| GET | `/api/claims/{claim_id}` | Full result for one claim |
| POST | `/api/rings/detect` | Stage 2: full detection run |
| GET | `/api/rings/latest` | Most recent stored run |
| GET | `/api/audit` | Append-only audit trail |
| GET | `/api/evaluation/metrics` | Precision / recall / AUC + ring metrics |
| POST | `/api/demo/bootstrap` | Generate data + run both stages |
| GET | `/api/demo/cost-of-delay` | ₹ exposure scenarios |
| POST | `/api/demo/simulate-webhook` | Sign + verify a Razorpay-shaped webhook |
| POST | `/api/webhooks/razorpay` | Signature-verified webhook receiver |

## Razorpay Test Mode integration

- Credentials load **only** from environment / `.env` via pydantic-settings —
  never hardcoded, never committed. Live keys (`rzp_live_*`) are rejected
  twice: at config level and again at client level.
- `razorpay_client.py` wraps the official SDK: fetch/create Test orders and
  payments, refunds, webhook HMAC verification.
- `data/razorpay_sync.py` pulls Test orders/payments into a local mirror,
  pushes generated orders via `order.create`, and enriches claims with real
  payment facts. All money actions stay in Test Mode.

## Honest evaluation

Ground-truth labels exist only in the synthetic dataset and are never visible
to any scorer (enforced by a test that inspects the pipeline source).
`/api/evaluation/metrics` reports claim-level precision / recall / F1 / AUC at
a chosen threshold, and member-level ring precision / recall against the
planted rings. Reference results from the built-in seed dataset:
**AUC ≈ 0.97, ring member precision ≈ 1.0** (threshold 0.6 → precision 1.0,
recall 0.4 — reported as measured, not tuned for looks).

## Testing

```bash
cd backend && .venv/Scripts/python -m pytest tests -q    # 113 tests
cd frontend && npm run build                             # type-checked build
```

Coverage includes: reuse/AI image forensics, all Stage 1 analyzers, the
strict ring-score formula, temporal burst vs. staggered detection,
cost-of-delay math, seeded-ring detection on generated datasets,
defense-only contract tests, and the API surface.

## Design system

Six tokens only — `background #0B0F14 · surface #151C26 · primary #4C8DFF ·
accent #8AE0B0 · danger #FF6B6B · text #E8EEF6` (defined once in
`tailwind.config.ts` and `lib/theme.ts`). Danger is reserved for risk, accent
for trust/verification. No two saturated colours are ever stacked; overlays
sit on blurred surface panels with generous whitespace.

## Deployment

Frontend runs on **Vercel**, backend on **Modal** (free tier, $30/month
credits, data baked at image build + persisted on a Modal Volume).
Step-by-step: [DEPLOY.md](DEPLOY.md).

## Repository layout

```
backend/    FastAPI · stage1/ · stage2/ · core/ · data/ · evaluation/ · routers · tests (113)
frontend/   Next.js 15 · components/{canvas,story,ui} · lib/ · 6-scene 3D story
DEPLOY.md   Vercel + Modal deployment guide
```

---

<div align="center">
Built for the Razorpay AI Buildathon 2026 · RefundShield never blocks, bans, or enforces — it only scores, explains, and logs.
</div>
