"use client";

import { motion } from "framer-motion";
import { Shield } from "lucide-react";

import { useStory } from "@/lib/store";

export function TopBar() {
  const rings = useStory((s) => s.rings);
  const error = useStory((s) => s.error);
  const bootstrapping = useStory((s) => s.bootstrapping);
  const runBootstrap = useStory((s) => s.runBootstrap);
  const hasData = Boolean(rings);

  return (
    <header className="absolute left-10 right-10 top-8 z-20 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15 text-primary">
          <Shield size={18} strokeWidth={2.2} />
        </span>
        <div>
          <p className="text-sm font-semibold tracking-tight">RefundShield</p>
          <p className="text-[10px] uppercase tracking-[0.25em] text-text/45">
            Defense-only AI risk manager
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {error && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-full border border-danger/40 bg-danger/10 px-3 py-1.5
              text-[11px] text-danger"
          >
            {error}
          </motion.span>
        )}
        {!hasData && (
          <button
            onClick={() => runBootstrap()}
            disabled={bootstrapping}
            className="rounded-full bg-primary px-4 py-2 text-xs font-medium
              text-background transition hover:brightness-110
              disabled:cursor-wait disabled:opacity-60"
          >
            {bootstrapping ? "Generating demo data…" : "Run demo pipeline"}
          </button>
        )}
        {hasData && (
          <span className="rounded-full border border-accent/40 bg-accent/10
            px-3 py-1.5 text-[11px] uppercase tracking-widest text-accent">
            Razorpay Test Mode
          </span>
        )}
      </div>
    </header>
  );
}
