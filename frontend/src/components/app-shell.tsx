"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "motion/react";
import {
  Activity,
  BookOpen,
  Bot,
  FileSearch,
  FlaskConical,
  LayoutDashboard,
  Library,
  Settings,
  ShieldAlert,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Logo } from "@/components/brand/logo";
import { openCommandMenu } from "@/components/command-menu";
import { clientApi } from "@/lib/api";
import type { Session } from "@/lib/types";
import { cn } from "@/lib/utils";

const groups = [
  {
    label: "Investigate",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/sandboxes", label: "Simulation Lab", icon: FlaskConical },
    ],
  },
  {
    label: "Test",
    items: [
      { href: "/agents", label: "Agents", icon: Bot },
      { href: "/programmes", label: "Programmes", icon: Activity },
      { href: "/library", label: "Scenario library", icon: Library },
      { href: "/assessments", label: "Assessments", icon: BookOpen },
    ],
  },
  {
    label: "Evidence",
    items: [
      { href: "/findings", label: "Findings", icon: ShieldAlert },
      { href: "/reports", label: "Reports", icon: FileSearch },
      { href: "/remediation", label: "Remediation", icon: Wrench },
    ],
  },
  {
    label: "Organisation",
    items: [
      { href: "/intelligence", label: "Intelligence", icon: Sparkles },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
] as const;

export function AppShell({ session, children }: { session: Session; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotion();

  useEffect(() => {
    document.body.classList.toggle("nav-open", open);
    return () => document.body.classList.remove("nav-open");
  }, [open]);

  async function logout() {
    await clientApi("/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  const nav = (
    <LayoutGroup id="aegis-nav">
      <nav aria-label="Workspace" className="flex flex-1 flex-col gap-4 overflow-y-auto px-2.5 py-4">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="px-2.5 pb-1.5 font-mono text-[9px] uppercase tracking-[0.18em] text-faint">{group.label}</p>
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "relative flex min-h-10 items-center gap-2.5 rounded-md px-2.5 text-[13px] transition-colors md:min-h-8",
                      active ? "text-foreground" : "text-muted-foreground hover:bg-white/[0.03] hover:text-foreground",
                    )}
                  >
                    {active ? (
                      <motion.span
                        layoutId={reduce ? undefined : "nav-active"}
                        className="absolute inset-0 rounded-md bg-white/[0.06] ring-1 ring-white/[0.06]"
                        transition={{ type: "spring", stiffness: 380, damping: 34 }}
                      />
                    ) : null}
                    <Icon className={cn("relative z-[1] h-3.5 w-3.5 shrink-0", active ? "text-signal" : "text-faint")} strokeWidth={1.75} />
                    <span className="relative z-[1]">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </LayoutGroup>
  );

  return (
    <div className="min-h-screen min-w-0">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[15.5rem] border-r border-border bg-panel/70 backdrop-blur-xl md:flex md:flex-col">
        <Link href="/dashboard" className="flex h-12 items-center border-b border-border px-4">
          <Logo />
        </Link>
        {nav}
        <div className="border-t border-border px-4 py-3">
          <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-faint">Organisation</p>
          <p className="mt-1 truncate text-[12px] text-muted-foreground">{session.organisation.name}</p>
        </div>
      </aside>

      <AnimatePresence>
        {open ? (
          <motion.div
            className="fixed inset-0 z-40 md:hidden"
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <button className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setOpen(false)} aria-label="Close navigation" />
            <motion.aside
              className="absolute inset-y-0 left-0 flex w-[min(18rem,88vw)] flex-col border-r border-border bg-panel pt-[env(safe-area-inset-top)]"
              initial={reduce ? false : { x: -24, opacity: 0.6 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -16, opacity: 0 }}
              transition={{ type: "spring", stiffness: 360, damping: 32 }}
            >
              <div className="flex h-12 items-center justify-between border-b border-border px-4">
                <Logo />
                <button onClick={() => setOpen(false)} className="grid h-9 w-9 place-items-center text-sm text-muted-foreground" aria-label="Close">
                  Close
                </button>
              </div>
              {nav}
              <div className="border-t border-border px-4 py-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
                <p className="truncate text-[13px] text-foreground">{session.user.full_name}</p>
                <p className="mt-1 truncate text-[12px] text-muted-foreground">{session.organisation.name}</p>
              </div>
            </motion.aside>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div className="min-w-0 md:pl-[15.5rem]">
        <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b border-border bg-canvas/75 px-3 pt-[env(safe-area-inset-top)] backdrop-blur-xl sm:px-4 md:px-6">
          <button className="grid h-9 w-9 shrink-0 place-items-center text-sm text-muted-foreground md:hidden" onClick={() => setOpen(true)} aria-label="Open navigation">
            Menu
          </button>
          <button
            type="button"
            onClick={openCommandMenu}
            className="hidden h-8 w-72 items-center justify-between rounded-md border border-border bg-inset/80 px-3 text-[12px] text-faint transition-colors hover:border-white/18 hover:text-muted-foreground md:flex"
          >
            Jump to…
            <kbd className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px]">Ctrl K</kbd>
          </button>
          <button
            type="button"
            onClick={openCommandMenu}
            className="grid h-9 w-9 place-items-center text-[13px] text-muted-foreground md:hidden"
            aria-label="Search pages"
          >
            Search
          </button>
          <div className="ml-auto flex min-w-0 items-center gap-3">
            <div className="min-w-0 text-right">
              <div className="truncate text-[12px] tracking-tight">{session.user.full_name}</div>
              <div className="hidden font-mono text-[9px] uppercase tracking-[0.16em] text-faint sm:block">{session.role}</div>
            </div>
            <span className="hidden h-5 w-px bg-border sm:block" aria-hidden="true" />
            <button onClick={logout} className="shrink-0 text-[12px] text-muted-foreground transition-colors hover:text-foreground">
              Log out
            </button>
          </div>
        </header>
        <main className="mx-auto w-full min-w-0 max-w-6xl px-4 py-5 sm:py-7 md:px-6">{children}</main>
      </div>
    </div>
  );
}
