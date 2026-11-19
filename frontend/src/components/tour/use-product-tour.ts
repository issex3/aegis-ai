"use client";

import { useCallback, useEffect, useRef } from "react";
import type { Driver } from "driver.js";
import "driver.js/dist/driver.css";
import { createAegisTourConfig, type AegisTourOptions } from "@/lib/tour";

/**
 * Client-only product tour hook. Dynamically loads driver.js on start.
 * Call destroy on unmount to avoid overlay leaks across App Router navigations.
 */
export function useProductTour() {
  const driverRef = useRef<Driver | null>(null);

  useEffect(() => {
    return () => {
      driverRef.current?.destroy();
      driverRef.current = null;
    };
  }, []);

  const start = useCallback(async (options: AegisTourOptions) => {
    driverRef.current?.destroy();
    const { driver } = await import("driver.js");
    driverRef.current = driver(createAegisTourConfig(options));
    driverRef.current.drive();
  }, []);

  const stop = useCallback(() => {
    driverRef.current?.destroy();
    driverRef.current = null;
  }, []);

  return { start, stop };
}
