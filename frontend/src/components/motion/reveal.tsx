"use client";

import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { aegisEase, fadeUp, staggerContainer, staggerItem } from "@/lib/motion-presets";

/** Animate in after mount so SSR/first paint stays visible. */
export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  if (reduce || !ready) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={fadeUp.initial}
      animate={fadeUp.animate}
      transition={{ ...fadeUp.transition, delay }}
    >
      {children}
    </motion.div>
  );
}

export function Stagger({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  if (reduce || !ready) {
    return <div className={cn(className)}>{children}</div>;
  }

  return (
    <motion.div className={cn(className)} initial="initial" animate="animate" variants={staggerContainer}>
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className} variants={staggerItem}>
      {children}
    </motion.div>
  );
}

export function SoftRise({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (reduce || !ready) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0.01, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: aegisEase }}
    >
      {children}
    </motion.div>
  );
}
