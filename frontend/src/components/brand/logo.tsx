import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true" className={cn("h-4 w-4", className)}>
      <path d="M2 2h16v10.5L10 18 2 12.5z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="miter" />
      <path d="M6 7.5h8" stroke="#e3a243" strokeWidth="1.4" />
      <path d="M6 10.5h5" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-[15px] font-medium tracking-[0.02em]", className)}>
      <LogoMark />
      Aegis <span className="text-[11px] font-normal uppercase tracking-[0.14em] text-faint">Beta</span>
    </span>
  );
}
