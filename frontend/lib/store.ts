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
  subtitle: string;
  camera: { pos: [number, number, number]; look: [number, number, number] };
}

export const SECTIONS: StorySection[] = [
  {
    id: "problem",
    index: "01",
    title: "The Problem",
    subtitle: "Refund abuse drains merchants quietly, claim by claim.",
    camera: { pos: [0, 3, 16], look: [0, 0, 0] },
  },
  {
    id: "claim",
    index: "02",
    title: "A Suspicious Claim",
    subtitle: "Stage 1 — four independent signals score one request.",
    camera: { pos: [5, 3.4, 8.5], look: [0, 0.6, 0] },
  },
  {
    id: "network",
    index: "03",
    title: "One Becomes Many",
    subtitle: "Shared devices, addresses and bank accounts link claims.",
    camera: { pos: [0, 7, 14], look: [0, 0, 0] },
  },
  {
    id: "rings",
    index: "04",
    title: "Rings Exposed",
    subtitle: "Stage 2 — Louvain communities become scored abuse rings.",
    camera: { pos: [0, 9, 15], look: [0, 0.5, 0] },
  },
  {
    id: "cost",
    index: "05",
    title: "Cost of Delay",
    subtitle: "What every unreviewed day costs, simulated in ₹.",
    camera: { pos: [0, 4.5, 13], look: [0, 1.2, 0] },
  },
  {
    id: "audit",
    index: "06",
    title: "Audit & Trust",
    subtitle: "Every decision is explained, logged, and reversible.",
    camera: { pos: [0, 2.5, 11], look: [0, 1.4, 0] },
  },
];

interface StoryData {
  claims: ClaimResultRow[];
  rings: RingDetectionResult | null;
  audit: AuditEvent[];
  loading: boolean;
  bootstrapping: boolean;
  error: string | null;
}

interface StoryState extends StoryData {
  section: number;
  setSection: (n: number) => void;
  next: () => void;
  prev: () => void;
  loadData: () => Promise<void>;
  runBootstrap: () => Promise<void>;
}

export const useStory = create<StoryState>((set, get) => ({
  section: 0,
  claims: [],
  rings: null,
  audit: [],
  loading: true,
  bootstrapping: false,
  error: null,

  setSection: (n) =>
    set({ section: Math.max(0, Math.min(SECTIONS.length - 1, n)) }),
  next: () => get().setSection(get().section + 1),
  prev: () => get().setSection(get().section - 1),

  loadData: async () => {
    set({ loading: true, error: null });
    try {
      const [claims, rings, audit] = await Promise.all([
        api.claims(),
        api.ringsLatest(),
        api.audit(),
      ]);
      set({ claims, rings, audit, loading: false });
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : "Backend unreachable",
      });
    }
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

/** Pick the most instructive claim for the Stage 1 deep-dive scene. */
export function spotlightClaim(claims: ClaimResultRow[]): ClaimResultRow | null {
  if (!claims.length) return null;
  const sorted = [...claims].sort(
    (a, b) => b.payload.image_evidence.ai_generated_score
      + b.risk_score
      - (a.payload.image_evidence.ai_generated_score + a.risk_score),
  );
  return sorted[0];
}
