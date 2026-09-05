"use client";

import dynamic from "next/dynamic";
import { useEffect } from "react";
import { useMotionValueEvent, useScroll } from "framer-motion";

import { ScrollRail } from "@/components/story/ScrollRail";
import {
  AuditPanel,
  ClaimPanel,
  CostPanel,
  HeroPanel,
  NetworkPanel,
  OutroPanel,
  RingsPanel,
} from "@/components/story/StoryOverlays";
import { TopBar } from "@/components/story/TopBar";
import { Loader } from "@/components/ui/Loader";
import { useStory } from "@/lib/store";

const StoryCanvas = dynamic(() => import("@/components/canvas/StoryCanvas"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full w-full place-items-center">
      <Loader label="Preparing the stage" />
    </div>
  ),
});

/** Chapter block: exactly one viewport tall, panel aligned to `side`. */
function Chapter({
  i,
  side,
  children,
}: {
  i: number;
  side: "left" | "right" | "center";
  children: React.ReactNode;
}) {
  const justify =
    side === "left" ? "justify-start" : side === "right" ? "justify-end" : "justify-center";
  return (
    <section
      id={`chapter-${i}`}
      className={`pointer-events-none relative flex h-screen snap-start items-center
        px-6 pb-28 pt-24 md:px-14 ${justify}`}
    >
      <div className={`pointer-events-auto flex w-full ${justify}`}>{children}</div>
    </section>
  );
}

export default function Home() {
  const loadData = useStory((s) => s.loadData);
  const setProgress = useStory((s) => s.setProgress);
  const { scrollYProgress } = useScroll();

  useMotionValueEvent(scrollYProgress, "change", (v) => setProgress(v));

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const s = useStory.getState();
      if (e.key === "ArrowDown" || e.key === "PageDown") {
        s.scrollToSection(Math.min(6, s.section + 1));
      }
      if (e.key === "ArrowUp" || e.key === "PageUp") {
        s.scrollToSection(Math.max(0, s.section - 1));
      }
      if (e.key === "Home") s.scrollToSection(0);
      if (e.key === "End") s.scrollToSection(6);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <main className="relative">
      {/* fixed 3D stage behind everything */}
      <div className="fixed inset-0 z-0">
        <StoryCanvas />
      </div>

      <TopBar />

      {/* scrolling story layer */}
      <div className="relative z-10">
        <Chapter i={0} side="center">
          <HeroPanel />
        </Chapter>
        <Chapter i={1} side="right">
          <ClaimPanel />
        </Chapter>
        <Chapter i={2} side="left">
          <NetworkPanel />
        </Chapter>
        <Chapter i={3} side="right">
          <RingsPanel />
        </Chapter>
        <Chapter i={4} side="left">
          <CostPanel />
        </Chapter>
        <Chapter i={5} side="right">
          <AuditPanel />
        </Chapter>
        <Chapter i={6} side="center">
          <OutroPanel />
        </Chapter>
      </div>

      <ScrollRail />
    </main>
  );
}
