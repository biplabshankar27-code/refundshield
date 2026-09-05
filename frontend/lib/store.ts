"use client";

import { create } from "zustand";

import { api } from "./api";
import type {
  AuditEvent,
  ClaimResultRow,
  RingDetectionResult,
} from "./types";

export interface StorySection {
  id: string;
  index: string;
  title: string;
  headline: string;
  subtitle: string;
  camera: { pos: [number, number, number]; look: [number, number, number] };
}

/**
 * Cinematic camera keyframes — bigger staging, alternating focal sides.
 * `look` is shifted toward panel-free space so 3D focal points never sit
 * behind the text panels (right panel → focus shifts left, etc.).
 */
export const SECTIONS: StorySection[] = [
  {
    id: "problem",
    index: "01",
    title: "The Problem",
    headline: "Every refund tells a story.",
    subtitle: "Refund abuse drains merchants quietly, claim by claim.",
    camera: { pos: [0, 2, 20], look: [0, 0, 0] },
  },
  {
    id: "claim",
    index: "02",
    title: "A Suspicious Claim",
    headline: "One request, four signals.",
    subtitle: "Stage 1 — four independent signals score one request.",
    camera: { pos: [6.5, 3.5, 10], look: [5.2, 0.4, 0] },
  },
  {
    id: "network",
    index: "03",
    title: "One Becomes Many",
    headline: "One claim becomes a network.",
    subtitle: "Shared devices, addresses and bank accounts link claims.",
    camera: { pos: [0, 8, 16], look: [-2.4, 0, 0] },
  },
  {
    id: "rings",
    index: "04",
    title: "Rings Exposed",
    headline: "Abuse rings, exposed.",
    subtitle: "Stage 2 — Louvain communities become scored abuse rings.",
    camera: { pos: [0, 11, 17], look: [1.8, 0.5, 0] },
  },
  {
    id: "cost",
    index: "05",
    title: "Cost of Delay",
    headline: "Waiting has a price, in ₹.",
    subtitle: "What every unreviewed day costs, simulated in ₹.",
    camera: { pos: [0, 4.5, 15], look: [-2.2, 1, 0] },
  },
  {
    id: "audit",
    index: "06",
    title: "Audit & Trust",
    headline: "Explained, logged, reversible.",
    subtitle: "Every decision is explained, logged, and reversible.",
    camera: { pos: [0, 2.5, 13], look: [2.6, 1.4, 0] },
  },
  {
    id: "outro",
    index: "END",
    title: "The Standard",
    headline: "Scores. Flags. Explanations. Logs.",
    subtitle: "Scores. Flags. Explanations. Logs.",
    camera: { pos: [0, 3.5, 15], look: [0, 1.3, 0] },
  },
];

export const SECTION_COUNT = SECTIONS.length;

interface StoryData {
  claims: ClaimResultRow[];
  rings: RingDetectionResult | null;
  audit: AuditEvent[];
  loading: boolean;
  bootstrapping: boolean;
  error: string | null;
}

interface StoryState extends StoryData {
  /** 0..1 scroll progress across the whole story. */
  progress: number;
  /** Discrete chapter 0..5 (derived from progress). */
  section: number;
  setProgress: (p: number) => void;
  scrollToSection: (i: number) => void;
  loadData: () => Promise<void>;
  runBootstrap: () => Promise<void>;
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

export const useStory = create<StoryState>((set, get) => ({
  section: 0,
  progress: 0,
  claims: [],
  rings: null,
  audit: [],
  loading: true,
  bootstrapping: false,
  error: null,

  setProgress: (p) =>
    set({
      progress: clamp01(p),
      section: Math.max(
        0,
        Math.min(SECTION_COUNT - 1, Math.round(clamp01(p) * (SECTION_COUNT - 1))),
      ),
    }),

  scrollToSection: (i) => {
    const vh = typeof window === "undefined" ? 800 : window.innerHeight;
    window.scrollTo({ top: i * vh, behavior: "smooth" });
  },

  loadData: async () => {
    set({ loading: true, error: null });
    // Retry a few times — the backend may be cold-starting (scale-to-zero).
    let lastError: unknown = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      if (attempt > 0) await new Promise((r) => setTimeout(r, 3500));
      try {
        const [claims, rings, audit] = await Promise.all([
          api.claims(),
          api.ringsLatest(),
          api.audit(),
        ]);
        set({ claims, rings, audit, loading: false, error: null });
        return;
      } catch (e) {
        lastError = e;
      }
    }
    set({
      loading: false,
      error: lastError instanceof Error ? lastError.message : "Backend unreachable",
    });
  },

  runBootstrap: async () => {
    set({ bootstrapping: true, error: null });
    try {
      await api.bootstrap();
      await get().loadData();
    } catch (e) {
      set({ error: e instanceof Error ? e.message : "Bootstrap failed" });
    } finally {
      set({ bootstrapping: false });
    }
  },
}));

/** Camera position at continuous scroll progress t (0..1). */
export function cameraAt(
  t: number,
): { pos: [number, number, number]; look: [number, number, number] } {
  const n = SECTION_COUNT - 1;
  const tt = clamp01(t) * n;
  const i = Math.min(Math.floor(tt), n - 1);
  const fRaw = tt - i;
  // smoothstep for cinematic easing between keyframes
  const f = fRaw * fRaw * (3 - 2 * fRaw);
  const a = SECTIONS[i].camera;
  const b = SECTIONS[i + 1].camera;
  const lerp = (x: number, y: number) => x + (y - x) * f;
  return {
    pos: [lerp(a.pos[0], b.pos[0]), lerp(a.pos[1], b.pos[1]), lerp(a.pos[2], b.pos[2])],
    look: [lerp(a.look[0], b.look[0]), lerp(a.look[1], b.look[1]), lerp(a.look[2], b.look[2])],
  };
}

/** Presence of scene `index` at progress t: 1 when centered, 0 far away. */
export function presenceAt(index: number, t: number): number {
  return Math.max(0, Math.min(1, 1 - Math.abs(index - clamp01(t) * (SECTION_COUNT - 1)) * 1.6));
}

/** Pick the most instructive claim for the Stage 1 deep-dive scene. */
export function spotlightClaim(claims: ClaimResultRow[]): ClaimResultRow | null {
  if (!claims.length) return null;
  const sorted = [...claims].sort(
    (a, b) =>
      b.payload.image_evidence.ai_generated_score +
      b.risk_score -
      (a.payload.image_evidence.ai_generated_score + a.risk_score),
  );
  return sorted[0];
}
