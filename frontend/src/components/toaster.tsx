"use client";

import { Toaster } from "sonner";

export function AppToaster() {
  return <Toaster position="bottom-right" toastOptions={{ style: { background: "#121218", color: "#e8eaed", border: "1px solid #2a2a34", borderRadius: 2 } }} />;
}
