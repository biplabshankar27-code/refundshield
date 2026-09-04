import { motion } from "framer-motion";

export function Loader({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1.1, ease: "linear" }}
        className="h-4 w-4 rounded-full border-2 border-text/20 border-t-primary"
      />
      <span className="text-sm text-text/60">{label}…</span>
    </div>
  );
}
