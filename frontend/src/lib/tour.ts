import type { Config, DriveStep } from "driver.js";

export type AegisTourOptions = Omit<Config, "steps" | "popoverClass"> & {
  steps: DriveStep[];
};

/**
 * Build a Driver.js config styled for Aegis.
 * Dynamically import `driver.js` in the caller so tours stay client-only.
 */
export function createAegisTourConfig(options: AegisTourOptions): Config {
  const reduce =
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return {
    animate: !reduce,
    overlayOpacity: 0.72,
    smoothScroll: !reduce,
    allowClose: true,
    stagePadding: 8,
    stageRadius: 2,
    popoverClass: "aegis-tour",
    showProgress: true,
    nextBtnText: "Next",
    prevBtnText: "Back",
    doneBtnText: "Done",
    ...options,
  };
}
