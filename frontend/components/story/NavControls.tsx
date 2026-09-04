"use client";

import { motion } from "framer-motion";

import { SECTIONS, useStory } from "@/lib/store";

export function NavControls() {
  const section = useStory((s) => s.section);
  const next = useStory((s) => s.next);
  const prev = useStory((s) => s.prev);
  const setSection = useStory((s) => s.setSection);
  const current = SECTIONS[section];

  return (
    <div className="absolute bottom-8 left-10 right-10 z-20 flex items-end justify-between">
      <div>
        <motion.p
          key={current.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-mono text-xs text-text/40"
        >
          {current.index} / 06
        </motion.p>
        <motion.h1
          key={current.id + "-title"}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mt-1 text-sm uppercase tracking-[0.25em] text-text/80"
        >
          {current.title}
        </motion.h1>
        <p className="mt-1 max-w-md text-xs text-text/45">{current.subtitle}</p>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={prev}
          disabled={section === 0}
          className="rounded-full border border-text/15 px-4 py-2 text-xs
            text-text/70 transition hover:border-primary hover:text-primary
            disabled:opacity-30 disabled:hover:border-text/15 disabled:hover:text-text/70"
        >
          ← Back
        </button>
        {section < SECTIONS.length - 1 ? (
          <button
            onClick={next}
            className="rounded-full bg-primary px-5 py-2 text-xs font-medium
              text-background transition hover:brightness-110"
          >
            Continue →
          </button>
        ) : (
          <button
            onClick={() => setSection(0)}
            className="rounded-full border border-accent/50 px-5 py-2 text-xs
              font-medium text-accent transition hover:bg-accent/10"
          >
            Replay story
          </button>
        )}
      </div>
    </div>
  );
}
