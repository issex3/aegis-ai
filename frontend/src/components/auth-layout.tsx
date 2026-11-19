import Link from "next/link";
import { Logo } from "@/components/brand/logo";

export function AuthLayout({
  title,
  description,
  aside,
  children,
}: {
  title: string;
  description: string;
  aside: { heading: string; points: string[] };
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_34rem]">
      <div className="relative hidden overflow-hidden border-r border-border lg:flex lg:flex-col lg:justify-between lg:p-12">
        <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full">
          <defs>
            <pattern id="auth-grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M24 0H0V24" fill="none" stroke="#ededea" strokeOpacity="0.03" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#auth-grid)" />
        </svg>
        <Link href="/" className="relative" aria-label="Aegis home">
          <Logo />
        </Link>
        <div className="relative max-w-md">
          <p className="text-3xl font-medium leading-tight tracking-[-0.03em]">
            {aside.heading}
          </p>
          <ul className="mt-8 border-t border-border">
            {aside.points.map((point) => (
              <li key={point} className="border-b border-border py-3 text-[13px] leading-6 text-muted-foreground">
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative font-mono text-[11px] text-faint">Assessment results are internal evidence, not certification.</p>
      </div>
      <div className="flex min-w-0 flex-col px-4 py-6 sm:px-12 sm:py-8" style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}>
        <Link href="/" className="lg:hidden" aria-label="Aegis home">
          <Logo />
        </Link>
        <ul className="mt-6 border-t border-border lg:hidden">
          {aside.points.map((point) => (
            <li key={point} className="border-b border-border py-2.5 text-[13px] leading-5 text-muted-foreground">
              {point}
            </li>
          ))}
        </ul>
        <div className="my-auto w-full max-w-sm py-8 sm:py-12">
          <h1 className="text-[26px] font-medium tracking-[-0.025em] sm:text-[28px]">{title}</h1>
          <p className="mb-8 mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
