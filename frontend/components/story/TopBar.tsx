"use client";

import { motion } from "framer-motion";
import { Shield } from "lucide-react";

import { useStory } from "@/lib/store";

export const REPO_URL = "https://github.com/biplabshankar27-code/refundshield";

/** GitHub mark (brand icons were removed from lucide-react). */
function GitHubMark({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

export function TopBar() {
  const rings = useStory((s) => s.rings);
  const error = useStory((s) => s.error);
  const bootstrapping = useStory((s) => s.bootstrapping);
  const runBootstrap = useStory((s) => s.runBootstrap);
  const section = useStory((s) => s.section);
  const hasData = Boolean(rings);

  return (
    <header className="absolute left-10 right-10 top-8 z-30 flex items-center justify-between">
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
        {section === 0 && (
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            title="View the source on GitHub"
            className="relative flex items-center gap-2 rounded-full border
              border-primary/40 bg-primary/10 px-4 py-2 text-xs font-medium
              text-primary transition hover:bg-primary/20"
          >
            {/* flashing halo */}
            <span
              aria-hidden
              className="absolute inset-0 animate-ping rounded-full border
                border-primary/50 opacity-40"
            />
            <GitHubMark />
            <span className="hidden sm:block">GitHub</span>
          </a>
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
