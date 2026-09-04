"use client";

import { SECTIONS, useStory } from "@/lib/store";

export function ProgressRail() {
  const section = useStory((s) => s.section);
  const setSection = useStory((s) => s.setSection);

  return (
    <nav className="absolute right-8 top-1/2 z-20 -translate-y-1/2 space-y-1">
      {SECTIONS.map((s, i) => {
        const activeCls =
          i === section
            ? "border-primary bg-primary/20"
            : i < section
              ? "border-text/30 bg-text/10"
              : "border-text/15";
        return (
          <button
            key={s.id}
            onClick={() => setSection(i)}
            title={s.title}
            className="group flex items-center justify-end gap-3 py-2"
          >
            <span className={`text-[10px] uppercase tracking-widest transition
              ${i === section ? "text-text" : "text-text/0 group-hover:text-text/50"}`}>
              {s.title}
            </span>
            <span className={`h-2.5 w-2.5 rounded-full border transition ${activeCls}`} />
          </button>
        );
      })}
    </nav>
  );
}
