"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "@/components/brand/logo";
import { openCommandMenu } from "@/components/command-menu";
import { cn } from "@/lib/utils";

const links = [
  { href: "/#product", label: "Product" },
  { href: "/#method", label: "Method" },
  { href: "/#sandboxes", label: "Sandboxes" },
  { href: "/#regression", label: "Regression" },
];

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.classList.toggle("nav-open", open);
    return () => document.body.classList.remove("nav-open");
  }, [open]);

  return (
    <header
      className={cn(
        "z-40 border-b pt-[env(safe-area-inset-top)] transition-colors duration-300",
        open ? "fixed inset-x-0 top-0" : "sticky top-0",
        scrolled || open ? "border-border bg-background/85 backdrop-blur-md" : "border-transparent bg-transparent",
      )}
    >
      <div className="mx-auto flex h-14 max-w-[1240px] items-center justify-between gap-3 px-4 sm:h-16 md:px-8">
        <Link href="/" aria-label="Aegis home" className="shrink-0">
          <Logo />
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-7 text-[13px] text-muted-foreground lg:flex">
          {links.map((link) => (
            <Link key={link.href} href={link.href} className="transition-colors hover:text-foreground">
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex min-w-0 items-center gap-2 text-[13px] sm:gap-4">
          <button
            type="button"
            onClick={openCommandMenu}
            className="hidden items-center gap-2 border border-border px-2 py-1 font-mono text-[11px] text-muted-foreground transition-colors hover:border-input hover:text-foreground md:inline-flex"
          >
            Search <kbd className="text-faint">Ctrl K</kbd>
          </button>
          <Link href="/login" className="hidden text-muted-foreground transition-colors hover:text-foreground sm:inline">
            Sign in
          </Link>
          <Link
            href="/register"
            className="inline-flex min-h-10 shrink-0 items-center bg-foreground px-3 py-1.5 text-[13px] font-medium text-background transition-opacity hover:opacity-90 sm:px-3"
          >
            <span className="sm:hidden">Start</span>
            <span className="hidden sm:inline">Start an assessment</span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="grid h-10 w-10 place-items-center text-muted-foreground lg:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
          >
            <span className="flex w-[18px] flex-col gap-[5px]" aria-hidden="true">
              <span className={cn("h-[1.5px] w-full bg-foreground transition-transform", open && "translate-y-[6.5px] rotate-45")} />
              <span className={cn("h-[1.5px] w-full bg-foreground transition-opacity", open && "opacity-0")} />
              <span className={cn("h-[1.5px] w-full bg-foreground transition-transform", open && "-translate-y-[6.5px] -rotate-45")} />
            </span>
          </button>
        </div>
      </div>
      {open ? (
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-border bg-background px-4 py-3 lg:hidden">
          {[...links, { href: "/login", label: "Sign in" }, { href: "/register", label: "Start an assessment" }].map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="flex min-h-12 items-center border-b border-border/70 text-[15px] text-foreground last:border-b-0"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}
