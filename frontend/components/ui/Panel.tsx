"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

/** Glass panel — the only overlay surface style allowed. */
export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 24 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className={`rounded-2xl border border-text/10 bg-surface/70 p-6 shadow-2xl shadow-black/40 backdrop-blur-xl ${className}`}
    >
      {children}
    </motion.div>
  );
}
