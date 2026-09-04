# RefundShield Frontend

A 3D storytelling experience (not a dashboard) built with Next.js 15,
React Three Fiber, drei, Tailwind CSS, Framer Motion and Zustand.

## Run

```bash
npm install
npm run dev        # http://localhost:3000
```

The backend is expected at `http://localhost:8000` — override with:

```bash
NEXT_PUBLIC_API_URL=http://my-host:8000 npm run dev
```

## The story (6 chapters)

| # | Chapter | 3D scene | Data |
|---|---------|----------|------|
| 01 | The Problem | drifting claim fragments, red minority pulses | rings exposure |
| 02 | A Suspicious Claim | claim card + orbiting signal satellites | real Stage 1 result |
| 03 | One Becomes Many | Fibonacci bloom of linked customers | shared-entity counts |
| 04 | Rings Exposed | member circles per detected ring | `/api/rings/latest` |
| 05 | Cost of Delay | growing ₹ bars (7/14/30 days) | cost-of-delay scenarios |
| 06 | Audit & Trust | rising audit helix around shield core | `/api/audit` |

Navigation: on-screen buttons, right-side rail, or arrow keys.

## Colour system (strict)

`background #0B0F14 · surface #151C26 · primary #4C8DFF · accent #8AE0B0 ·
danger #FF6B6B · text #E8EEF6` — defined once in `tailwind.config.ts` and
`lib/theme.ts`. Danger is reserved for risk, accent for trust/verification.
Overlays always sit on blurred surface panels — never colour-on-colour.

## Build

```bash
npm run build
npm start
```
