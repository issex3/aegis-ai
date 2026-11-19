/** Shared Motion presets — purposeful, premium, reduced-motion aware. */

export const aegisEase = [0.22, 1, 0.36, 1] as const;

export const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, ease: aegisEase },
} as const;

export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.28, ease: aegisEase },
} as const;

export const riseSoft = {
  initial: { opacity: 0, y: 10, filter: "blur(4px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  transition: { duration: 0.5, ease: aegisEase },
} as const;

export const staggerContainer = {
  animate: {
    transition: { staggerChildren: 0.055, delayChildren: 0.04 },
  },
} as const;

export const staggerItem = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: aegisEase } },
} as const;

/** Collapse motion when the user prefers reduced motion. */
export function motionSafe<T extends Record<string, unknown>>(
  reduce: boolean | null,
  next: T,
): T | false {
  return reduce ? false : next;
}
