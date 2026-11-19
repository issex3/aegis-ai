"use client";

import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/** Compact animated metric — only for real values. */
export function NumberTicker({
  value,
  className,
  decimals = 0,
}: {
  value: number;
  className?: string;
  decimals?: number;
}) {
  const reduce = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  const motionValue = useMotionValue(value);
  const spring = useSpring(motionValue, { stiffness: 110, damping: 24, mass: 0.55 });
  const display = useTransform(spring, (latest) =>
    Number(latest).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }),
  );

  useEffect(() => {
    setMounted(true);
    motionValue.set(0);
    const id = requestAnimationFrame(() => motionValue.set(value));
    return () => cancelAnimationFrame(id);
  }, [motionValue, value]);

  if (reduce || !mounted) {
    return <span className={cn("tabular", className)}>{value.toLocaleString()}</span>;
  }

  return <motion.span className={cn("tabular", className)}>{display}</motion.span>;
}
