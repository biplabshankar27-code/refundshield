"use client";

import dynamic from "next/dynamic";
import { useEffect } from "react";

import { NavControls } from "@/components/story/NavControls";
import { ProgressRail } from "@/components/story/ProgressRail";
import { StoryOverlays } from "@/components/story/StoryOverlays";
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

export default function Home() {
  const loadData = useStory((s) => s.loadData);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const store = useStory.getState();
      if (e.key === "ArrowRight" || e.key === "PageDown") store.next();
      if (e.key === "ArrowLeft" || e.key === "PageUp") store.prev();
      if (e.key === "Home") store.setSection(0);
      if (e.key === "End") store.setSection(5);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <main className="relative h-screen w-screen overflow-hidden">
      {/* 3D story layer */}
      <div className="absolute inset-0">
        <StoryCanvas />
      </div>

      {/* HTML overlay layer */}
      <TopBar />
      <StoryOverlays />
      <ProgressRail />
      <NavControls />
    </main>
  );
}
