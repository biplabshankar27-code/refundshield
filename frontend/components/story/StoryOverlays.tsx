"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { spotlightClaim, useStory } from "@/lib/store";
import { Loader } from "@/components/ui/Loader";
import { Panel } from "@/components/ui/Panel";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SignalBar } from "@/components/ui/SignalBar";
import { Stat } from "@/components/ui/Stat";
import { SECTIONS } from "@/lib/store";

const inr = (v: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(v);

const reveal = {
  initial: { opacity: 0, y: 48 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { amount: 0.45 as const, margin: "-8% 0px" as const },
  transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const },
};

function ChapterHeading({ i }: { i: number }) {
  const s = SECTIONS[i];
  return (
    <div className="space-y-2">
      <p className="text-[11px] font-medium uppercase tracking-[0.35em] text-primary">
        Chapter {s.index} · {s.title}
      </p>
      <h2 className="text-3xl font-semibold leading-tight md:text-4xl">
        {s.headline}
      </h2>
      <div className="h-px w-16 bg-primary/50" />
    </div>
  );
}

function Body({ children }: { children: ReactNode }) {
  return (
    <p className="text-sm leading-7 text-text/70 md:text-base md:leading-8">
      {children}
    </p>
  );
}

/** One glass panel — the single overlay surface style. */
function Glass({
  children,
  side,
  i,
}: {
  children: ReactNode;
  side: "left" | "right" | "center";
  i: number;
}) {
  const justify =
    side === "left" ? "justify-start" : side === "right" ? "justify-end" : "justify-center";
  return (
    <motion.div {...reveal} className={`flex w-full max-w-6xl ${justify}`}>
      <motion.div
        initial={false}
        className={`w-full ${side === "center" ? "max-w-2xl text-center" : "max-w-xl"}`}
      >
        <Panel className="p-8 md:p-10">
          <div className={side === "center" ? "space-y-6" : "space-y-7"}>
            {i >= 0 && <ChapterHeading i={i} />}
            {children}
          </div>
        </Panel>
      </motion.div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ hero */
export function HeroPanel() {
  const rings = useStory((s) => s.rings);
  const exposure = rings?.rings.reduce((a, r) => a + r.estimated_exposure_inr, 0);
  return (
    <motion.div
      {...reveal}
      className="text-scrim flex w-full max-w-4xl flex-col items-center text-center"
    >
      <p className="text-[11px] font-medium uppercase tracking-[0.4em] text-primary">
        Chapter 01 · The Problem
      </p>
      <h1 className="mt-5 text-5xl font-semibold leading-[1.05] tracking-tight md:text-7xl">
        Every refund tells
        <br />
        <span className="text-primary">a story.</span> We read them all.
      </h1>
      <p className="mt-7 max-w-2xl text-base leading-8 text-text/70 md:text-lg md:leading-9">
        Fraudulent refund claims rarely arrive alone — they find each other.
        RefundShield is a two-stage, defense-only risk system that detects
        fraud, uncovers organized rings, and explains every decision.
      </p>
      <div className="mt-10 grid w-full max-w-lg grid-cols-2 gap-8 border-y border-text/10 py-6">
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
      <div className="mt-9 flex items-center gap-3 text-xs uppercase tracking-[0.3em] text-text/45">
        <motion.span
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 1.6, ease: "easeInOut" }}
          className="text-primary"
        >
          ↓
        </motion.span>
        Scroll to begin
      </div>
    </motion.div>
  );
}

export function ClaimPanel() {
  const claims = useStory((s) => s.claims);
  const claim = spotlightClaim(claims);
  return (
    <Glass i={1} side="right">
      {claim ? (
        <>
          <div className="flex items-center justify-between gap-4">
            <span className="font-mono text-base">{claim.claim_id}</span>
            <RiskBadge band={claim.risk_band} />
          </div>
          <div className="grid grid-cols-2 gap-8 border-y border-text/10 py-5">
            <Stat label="Risk score" value={claim.risk_score.toFixed(2)} tone="danger" />
            <Stat label="Priority" value={claim.review_priority.replace("_", " ")} />
          </div>
          <div className="space-y-4">
            {claim.payload.signals.map((s, i) => (
              <SignalBar key={s.name} index={i} {...s} />
            ))}
          </div>
          <p className="border-l-2 border-primary/60 pl-4 text-xs leading-6 text-text/70 md:text-sm">
            {claim.reason}
          </p>
        </>
      ) : (
        <div className="py-4"><Loader label="Analyzing claims" /></div>
      )}
    </Glass>
  );
}

export function NetworkPanel() {
  const rings = useStory((s) => s.rings);
  const entities = rings?.rings.flatMap((r) =>
    Object.entries(r.shared_entities).map(([kind, list]) => ({ kind, n: list.length })),
  ) ?? [];
  const byKind = entities.reduce<Record<string, number>>((acc, e) => {
    acc[e.kind] = (acc[e.kind] ?? 0) + e.n;
    return acc;
  }, {});
  return (
    <Glass i={2} side="left">
      <Body>
        Customers are connected when they share a device, a shipping address, a
        refund bank account — or the exact same evidence photo.
      </Body>
      <div className="grid grid-cols-4 gap-6 border-t border-text/10 pt-6">
        <Stat label="Devices" value={String(byKind.device ?? 0)} />
        <Stat label="Addresses" value={String(byKind.address ?? 0)} />
        <Stat label="Banks" value={String(byKind.vpa ?? 0)} />
        <Stat label="Photos" value={String(byKind.image ?? 0)} tone="danger" />
      </div>
    </Glass>
  );
}

export function RingsPanel() {
  const rings = useStory((s) => s.rings);
  const top = (rings?.rings ?? []).slice(0, 3);
  return (
    <Glass i={3} side="right">
      {top.length ? (
        <>
          <div className="space-y-4">
            {top.map((r) => (
              <div key={r.ring_id}
                className="rounded-2xl border border-text/10 bg-background/50 p-5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{r.ring_id}</span>
                  <RiskBadge band={r.risk_band} />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-4">
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
          </div>
          <p className="text-[11px] leading-6 text-text/50 md:text-xs">
            ring_score = 0.6 × avg claim risk + 0.4 × graph density. Temporal
            coordination informs the flags, never the formula.
          </p>
        </>
      ) : (
        <div className="py-4"><Loader label="Detecting rings" /></div>
      )}
    </Glass>
  );
}

export function CostPanel() {
  const rings = useStory((s) => s.rings);
  const cod = rings?.cost_of_delay;
  const s = cod?.scenarios ?? {};
  return (
    <Glass i={4} side="left">
      <Body>
        Open ring exposure, compounded daily at the observed activity rate of
        the detected rings.
      </Body>
      <div className="grid grid-cols-2 gap-8 border-t border-text/10 pt-6">
        <Stat label="Daily burn"
          value={cod ? inr(cod.daily_exposure_inr) : "—"} tone="danger" />
        <Stat label="In 7 days" value={s["7"] ? inr(s["7"]) : "—"} />
        <Stat label="In 14 days" value={s["14"] ? inr(s["14"]) : "—"} />
        <Stat label="In 30 days" value={s["30"] ? inr(s["30"]) : "—"}
          tone="danger" />
      </div>
      {cod?.note && (
        <p className="text-[11px] leading-6 text-text/50 md:text-xs">{cod.note}</p>
      )}
    </Glass>
  );
}

export function AuditPanel() {
  const audit = useStory((s) => s.audit);
  return (
    <Glass i={5} side="right">
      <div className="flex flex-wrap gap-3">
        <span className="rounded-full border border-accent/40 bg-accent/10 px-4 py-1.5 text-[11px] uppercase tracking-widest text-accent">
          Defense-only
        </span>
        <span className="rounded-full border border-text/15 px-4 py-1.5 text-[11px] uppercase tracking-widest text-text/60">
          No auto-blocking, ever
        </span>
      </div>
      <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
        {audit.slice(0, 8).map((e) => (
          <div key={e.id}
            className="flex items-baseline justify-between gap-4 rounded-xl border border-text/10 bg-background/50 px-4 py-2.5">
            <span className="shrink-0 font-mono text-[11px] text-primary">{e.event_type}</span>
            <span className="truncate text-[11px] text-text/60 md:text-xs">{e.summary}</span>
          </div>
        ))}
        {audit.length === 0 && <Loader label="Reading audit trail" />}
      </div>
      <p className="text-[11px] leading-6 text-text/50 md:text-xs">
        Every score, every ring, every Razorpay interaction is written to an
        append-only SQLite audit trail.
      </p>
    </Glass>
  );
}

export function OutroPanel() {
  const scrollToSection = useStory((s) => s.scrollToSection);
  return (
    <Glass i={-1} side="center">
      <h2 className="text-3xl font-semibold md:text-4xl">
        Scores. Flags. Explanations. Logs.
      </h2>
      <Body>
        RefundShield never blocks accounts or takes enforcement action — every
        finding lands in a human review queue with the full story attached.
      </Body>
      <div className="flex justify-center">
        <button
          onClick={() => scrollToSection(0)}
          className="rounded-full border border-accent/50 px-6 py-2.5 text-sm
            font-medium text-accent transition hover:bg-accent/10"
        >
          Replay the story ↑
        </button>
      </div>
    </Glass>
  );
}
