"use client";

import { AnimatePresence, motion } from "framer-motion";

import { SECTIONS, spotlightClaim, useStory } from "@/lib/store";
import { Panel } from "@/components/ui/Panel";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SignalBar } from "@/components/ui/SignalBar";
import { Stat } from "@/components/ui/Stat";
import { Loader } from "@/components/ui/Loader";

const inr = (v: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(v);

export function StoryOverlays() {
  const section = useStory((s) => s.section);
  const Current = OVERLAYS[section];
  return (
    <div className="pointer-events-none absolute inset-0 z-10">
      <AnimatePresence mode="wait">
        <Current key={SECTIONS[section].id} />
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------ 01 problem */
function ProblemOverlay() {
  const rings = useStory((s) => s.rings);
  const exposure = rings?.rings.reduce((a, r) => a + r.estimated_exposure_inr, 0);
  return (
    <Wrapper>
      <Panel className="max-w-md">
        <p className="text-xs uppercase tracking-[0.3em] text-primary">
          Chapter 01 · The Problem
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-tight">
          Every refund desk is quietly bleeding.
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-text/70">
          Fraudulent refund and return requests rarely arrive alone. Each
          red fragment drifting past is a claim that doesn&apos;t add up —
          and they find each other.
        </p>
        <div className="mt-6 grid grid-cols-2 gap-6">
          <Stat
            label="Open exposure"
            value={exposure ? inr(exposure) : "—"}
            tone="danger"
          />
          <Stat
            label="Rings detected"
            value={rings ? String(rings.rings.length) : "—"}
          />
        </div>
      </Panel>
    </Wrapper>
  );
}

/* -------------------------------------------------------------- 02 claim */
function ClaimOverlay() {
  const claims = useStory((s) => s.claims);
  const claim = spotlightClaim(claims);
  return (
    <Wrapper side="right">
      <Panel className="w-[380px]">
        <p className="text-xs uppercase tracking-[0.3em] text-primary">
          Chapter 02 · Stage 1
        </p>
        {claim ? (
          <>
            <div className="mt-3 flex items-center justify-between gap-3">
              <h2 className="font-mono text-lg">{claim.claim_id}</h2>
              <RiskBadge band={claim.risk_band} />
            </div>
            <div className="mt-4 flex items-end justify-between">
              <Stat label="Risk score"
                value={claim.risk_score.toFixed(2)} tone="danger" />
              <Stat label="Priority"
                value={claim.review_priority.replace("_", " ")} />
            </div>
            <div className="mt-5 space-y-4">
              {claim.payload.signals.map((s, i) => (
                <SignalBar key={s.name} index={i} {...s} />
              ))}
            </div>
            <p className="mt-5 border-l-2 border-primary/60 pl-3 text-xs leading-relaxed text-text/70">
              {claim.reason}
            </p>
          </>
        ) : (
          <div className="mt-6"><Loader label="Analyzing claims" /></div>
        )}
      </Panel>
    </Wrapper>
  );
}

/* ------------------------------------------------------------- 03 network */
function NetworkOverlay() {
  const rings = useStory((s) => s.rings);
  const entities = rings?.rings.flatMap((r) =>
    Object.entries(r.shared_entities).map(([kind, list]) => ({ kind, n: list.length })),
  ) ?? [];
  const byKind = entities.reduce<Record<string, number>>((acc, e) => {
    acc[e.kind] = (acc[e.kind] ?? 0) + e.n;
    return acc;
  }, {});
  return (
    <Wrapper>
      <Panel className="max-w-md">
        <p className="text-xs uppercase tracking-[0.3em] text-primary">
          Chapter 03 · The Link
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-tight">
          One claim becomes a network.
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-text/70">
          Customers are connected when they share a device, a shipping
          address, a refund bank account — or the exact same evidence photo.
        </p>
        <div className="mt-6 grid grid-cols-4 gap-4">
          <Stat label="Devices" value={String(byKind.device ?? 0)} />
          <Stat label="Addresses" value={String(byKind.address ?? 0)} />
          <Stat label="Banks" value={String(byKind.vpa ?? 0)} />
          <Stat label="Photos" value={String(byKind.image ?? 0)} tone="danger" />
        </div>
      </Panel>
    </Wrapper>
  );
}

/* --------------------------------------------------------------- 04 rings */
function RingOverlay() {
  const rings = useStory((s) => s.rings);
  const top = (rings?.rings ?? []).slice(0, 3);
  return (
    <Wrapper side="right">
      <Panel className="w-[400px]">
        <p className="text-xs uppercase tracking-[0.3em] text-primary">
          Chapter 04 · Stage 2
        </p>
        <h2 className="mt-3 text-2xl font-semibold">Abuse rings, exposed.</h2>
        {top.length ? (
          <div className="mt-5 space-y-4">
            {top.map((r) => (
              <div key={r.ring_id}
                className="rounded-xl border border-text/10 bg-background/40 p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{r.ring_id}</span>
                  <RiskBadge band={r.risk_band} />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-3">
                  <Stat label="Score" value={r.ring_score.toFixed(2)}
                    tone={r.risk_band === "high" || r.risk_band === "critical" ? "danger" : "text"} />
                  <Stat label="Members" value={String(r.size)} />
                  <Stat label="Exposure" value={inr(r.estimated_exposure_inr)} />
                </div>
                {r.adversarial_flags.length > 0 && (
                  <p className="mt-3 text-[11px] uppercase tracking-wider text-danger">
                    ⚠ {r.adversarial_flags[0]}
                  </p>
                )}
              </div>
            ))}
            <p className="text-[11px] leading-relaxed text-text/50">
              ring_score = 0.6 × avg claim risk + 0.4 × graph density.
              Temporal coordination informs the flags, never the formula.
            </p>
          </div>
        ) : (
          <div className="mt-6"><Loader label="Detecting rings" /></div>
        )}
      </Panel>
    </Wrapper>
  );
}

/* ---------------------------------------------------------------- 05 cost */
function CostOverlay() {
  const rings = useStory((s) => s.rings);
  const cod = rings?.cost_of_delay;
  const s = cod?.scenarios ?? {};
  return (
    <Wrapper>
      <Panel className="max-w-md">
        <p className="text-xs uppercase tracking-[0.3em] text-primary">
          Chapter 05 · Cost of Delay
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-tight">
          Waiting has a price, in ₹.
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-text/70">
          Open ring exposure, compounded daily at the observed activity
          rate of the detected rings.
        </p>
        <div className="mt-6 grid grid-cols-2 gap-6">
          <Stat label="Daily burn"
            value={cod ? inr(cod.daily_exposure_inr) : "—"} tone="danger" />
          <Stat label="In 7 days" value={s["7"] ? inr(s["7"]) : "—"} />
          <Stat label="In 14 days" value={s["14"] ? inr(s["14"]) : "—"} />
          <Stat label="In 30 days" value={s["30"] ? inr(s["30"]) : "—"}
            tone="danger" />
        </div>
        {cod?.note && (
          <p className="mt-5 text-[11px] leading-relaxed text-text/50">{cod.note}</p>
        )}
      </Panel>
    </Wrapper>
  );
}

/* --------------------------------------------------------------- 06 audit */
function AuditOverlay() {
  const audit = useStory((s) => s.audit);
  return (
    <Wrapper side="right">
      <Panel className="w-[420px]">
        <p className="text-xs uppercase tracking-[0.3em] text-primary">
          Chapter 06 · Audit &amp; Trust
        </p>
        <h2 className="mt-3 text-2xl font-semibold">
          Explained, logged, reversible.
        </h2>
        <div className="mt-4 flex gap-2">
          <span className="rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-[11px] uppercase tracking-widest text-accent">
            Defense-only
          </span>
          <span className="rounded-full border border-text/15 px-3 py-1 text-[11px] uppercase tracking-widest text-text/60">
            No auto-blocking, ever
          </span>
        </div>
        <div className="mt-5 max-h-56 space-y-2 overflow-hidden">
          {audit.slice(0, 6).map((e) => (
            <div key={e.id}
              className="flex items-baseline justify-between gap-3 rounded-lg border border-text/10 bg-background/40 px-3 py-2">
              <span className="font-mono text-[11px] text-primary">{e.event_type}</span>
              <span className="truncate text-[11px] text-text/60">{e.summary}</span>
            </div>
          ))}
          {audit.length === 0 && <Loader label="Reading audit trail" />}
        </div>
        <p className="mt-4 text-[11px] leading-relaxed text-text/50">
          Every score, every ring, every Razorpay interaction is written to an
          append-only SQLite audit trail.
        </p>
      </Panel>
    </Wrapper>
  );
}

/* ---------------------------------------------------------------- helpers */
const OVERLAYS = [
  ProblemOverlay,
  ClaimOverlay,
  NetworkOverlay,
  RingOverlay,
  CostOverlay,
  AuditOverlay,
];

function Wrapper({
  children,
  side = "left",
}: {
  children: React.ReactNode;
  side?: "left" | "right";
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 30 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
      className={`pointer-events-auto absolute bottom-24 ${
        side === "left" ? "left-10" : "right-10"
      } max-w-[92vw]`}
    >
      {children}
    </motion.div>
  );
}
