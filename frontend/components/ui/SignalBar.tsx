import { motion } from "framer-motion";

const LABELS: Record<string, string> = {
  image_evidence: "Image evidence",
  history_evidence: "Customer history",
  payment_delivery_evidence: "Payment & delivery",
  text_evidence: "Claim text",
};

/** Horizontal risk bar. Colour ramps primary → danger only; never stacked hues. */
export function SignalBar({
  name,
  score,
  weight,
  detail,
  index = 0,
}: {
  name: string;
  score: number;
  weight: number;
  detail: string;
  index?: number;
}) {
  const danger = score >= 0.6;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-xs font-medium uppercase tracking-wider text-text/70">
          {LABELS[name] ?? name}
        </span>
        <span className={`font-mono text-xs ${danger ? "text-danger" : "text-text/80"}`}>
          {score.toFixed(2)}
          <span className="text-text/40"> · w{weight.toFixed(2)}</span>
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-text/10">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.round(score * 100)}%` }}
          transition={{ duration: 0.9, delay: 0.15 * index, ease: "easeOut" }}
          className={`h-full rounded-full ${danger ? "bg-danger" : "bg-primary"}`}
        />
      </div>
      {detail ? (
        <p className="text-[11px] leading-snug text-text/50">{detail}</p>
      ) : null}
    </div>
  );
}
