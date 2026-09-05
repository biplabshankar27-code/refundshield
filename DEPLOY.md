# Deploying RefundShield for free

Frontend → **Vercel** · Backend → **Modal** ($30/month free credits, no card).
Backend cold start after idle: a few seconds; data is baked in at build time
and persisted on a Modal Volume.

---

## 0 · Live deployment (Sep 2026)

| Piece | URL |
|---|---|
| Frontend (production) | https://refundshield-biplab.vercel.app |
| Backend (Modal) | https://biplabshankar27-code--refundshield-api.modal.run |
| API docs (Swagger) | https://biplabshankar27-code--refundshield-api.modal.run/docs |

Verified live: `/health` ok · 3 rings served from the baked seed · CORS
preflight passes for the Vercel origin (regex allows any `*.vercel.app`
domain, so project renames need no backend change) · API URL inlined in the
client bundle.

One manual step remains: in Vercel → Project **bitwisers/frontend** →
Settings → Deployment Protection → set **Vercel Authentication** to *Off*
so the stable domain `frontend-bitwisers.vercel.app` is public too (the
alias URL above is already public).

---

## 1 · Backend on Modal

### One-time setup

```bash
cd backend
pip install modal          # deploy tool only — not a runtime dependency
modal setup                # browser auth
```

Create the secret (hold your keys, never in code):

```bash
modal secret create refundshield-secrets \
  RAZORPAY_KEY_ID=rzp_test_TY215AVbZ1GTwn \
  RAZORPAY_KEY_SECRET=<your-key-secret> \
  CORS_ORIGINS=https://<your-app>.vercel.app
```

> The secret name must be exactly `refundshield-secrets` (referenced in
> `modal_app.py`). Keys live only in Modal's secret store.

### Deploy

```bash
modal deploy modal_app.py
```

This builds the image once — the build step (`prepare_seed`) generates the
synthetic dataset, runs Stage 1 + Stage 2, and bakes a ready `refundshield.db`
into the image. Deploy prints the public URL, e.g.:

```
https://<your-workspace>--refundshield-api.modal.run
```

Verify it:

```bash
curl https://<your-workspace>--refundshield-api.modal.run/health
curl https://<your-workspace>--refundshield-api.modal.run/api/rings/latest
```

Rings data is already populated from the baked seed — no bootstrap needed.

### How it behaves at runtime

| Aspect | Behaviour |
|---|---|
| Cold start | A few seconds after ~10 min idle (`scaledown_window=600`) |
| Persistence | Modal Volume `refundshield-data` mounted at `/data` — new claims, runs, and audit events survive restarts |
| Seed | Baked DB copied to the volume only if the volume is empty |
| Writers | `max_containers=1` — a single SQLite writer, no lock contention |
| Cost | ~$1–2 of the $30 monthly credit for typical demo usage |

### Re-deploy / update

```bash
modal deploy modal_app.py          # new image build re-seeds a fresh dataset
```

The volume keeps existing data; a fresh deploy's baked seed only applies if
the volume is empty. To reset everything:

```bash
modal volume rm refundshield-data refundshield.db
```

---

## 2 · Frontend on Vercel

1. Push the repo to GitHub.
2. Vercel → **Add New Project** → import the repo.
3. **Root Directory:** `frontend`
4. Environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://<your-workspace>--refundshield-api.modal.run`
5. Deploy. Open the app and press **"Run demo pipeline"** once if you want a
   larger dataset than the baked seed (runs live on Modal).

---

## 3 · Razorpay notes

- The deployed backend uses the keys **only from the Modal secret** — the same
  enforcement as local (`.env` never committed, `rzp_live_*` refused twice).
- All money operations remain **Test Mode**. The live-verification round trip
  (create + fetch a test order) is performed by the `razorpay_client.py` wrapper.

---

## 4 · Troubleshooting

| Symptom | Fix |
|---|---|
| First request slow after idle | Normal cold start (~seconds). Baked data means it's still instant-content once up. |
| CORS errors from the Vercel domain | Recreate the secret with `CORS_ORIGINS=https://<your-app>.vercel.app` and `modal deploy` again |
| "Secret not found" at deploy | Run the `modal secret create refundshield-secrets ...` command |
| Want a bigger demo dataset | Press **Run demo pipeline** in the UI (persists on the volume), or POST `/api/demo/bootstrap` |
| Logs | `modal app logs refundshield` (or the dashboard) |
