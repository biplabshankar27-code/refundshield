/** Shared colour tokens — single source of truth for the visual system. */
export const PALETTE = {
  background: "#0B0F14",
  surface: "#151C26",
  primary: "#4C8DFF",
  accent: "#8AE0B0",
  danger: "#FF6B6B",
  text: "#E8EEF6",
} as const;

export type PaletteKey = keyof typeof PALETTE;
