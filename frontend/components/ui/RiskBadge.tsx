import type { RiskBand } from "@/lib/types";

const STYLES: Record<RiskBand, string> = {
  low: "border-accent/40 bg-accent/10 text-accent",
  medium: "border-primary/40 bg-primary/10 text-primary",
  high: "border-danger/50 bg-danger/10 text-danger",
  critical: "border-danger bg-danger/20 text-danger",
};

export function RiskBadge({ band }: { band: RiskBand }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-widest ${STYLES[band]}`}
    >
      {band}
    </span>
  );
}
