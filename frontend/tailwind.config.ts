import type { Config } from "tailwindcss";

/**
 * RefundShield design tokens.
 * Strict 6-colour system: background, surface, primary, accent, danger, text.
 * Rule: never place two high-saturation colours on top of each other.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0F14", // deep space — page background
        surface: "#151C26", // raised panels / cards
        primary: "#4C8DFF", // calm blue — brand + structure
        accent: "#8AE0B0", // soft mint — positive / explanation
        danger: "#FF6B6B", // coral — risk only
        text: "#E8EEF6", // near-white — typography
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      spacing: {
        section: "min(14vh, 9rem)",
      },
    },
  },
  plugins: [],
};

export default config;
