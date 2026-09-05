"use client";

import { motion } from "framer-motion";

import { SECTIONS, useStory } from "@/lib/store";

/** Fixed horizontal chapter rail — scroll position indicator + navigation. */
export function ScrollRail() {
  const section = useStory((s) => s.section);
  const scrollToSection = useStory((s) => s.scrollToSection);

  return (
    <nav className="fixed bottom-7 left-1/2 z-30 -translate-x-1/2">
      <div className="flex items-center gap-2 rounded-full border border-text/10
        bg-surface/70 px-4 py-2.5 shadow-2xl shadow-black/50 backdrop-blur-xl">
        {SECTIONS.map((s, i) => (
          <button
            key={s.id}
            onClick={() => scrollToSection(i)}
            title={`${s.index} · ${s.title}`}
            className="group relative grid h-8 w-8 place-items-center"
          >
            <span className={`rounded-full transition-all duration-300 ${
              i === section
                ? "h-2.5 w-8 bg-primary"
                : i < section
                  ? "h-2 w-2 bg-text/40"
                  : "h-2 w-2 bg-text/15 group-hover:bg-text/40"
            }`} />
          </button>
        ))}
        <motion.span
          key={section}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="ml-2 hidden font-mono text-[10px] uppercase tracking-[0.25em] text-text/50 sm:block"
        >
          {SECTIONS[section].index}
        </motion.span>
      </div>
    </nav>
  );
}
