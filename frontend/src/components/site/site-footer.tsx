import Link from "next/link";
import { Logo } from "@/components/brand/logo";

const groups = [
  {
    title: "Product",
    links: [
      { href: "/#product", label: "Assessment record" },
      { href: "/#sandboxes", label: "Industry sandboxes" },
      { href: "/#regression", label: "Regression" },
      { href: "/demo", label: "Demonstration" },
    ],
  },
  {
    title: "Documentation",
    links: [
      { href: "/legal/methodology", label: "Methodology" },
      { href: "/legal/responsible-testing", label: "Responsible testing" },
      { href: "/legal/contribution", label: "Data contribution" },
      { href: "/legal/retention", label: "Data retention" },
    ],
  },
  {
    title: "Legal drafts",
    links: [
      { href: "/legal/privacy", label: "Privacy" },
      { href: "/legal/terms", label: "Terms" },
      { href: "/legal/acceptable-use", label: "Acceptable use" },
      { href: "/legal/licensing", label: "Dataset licensing" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto grid max-w-[1240px] grid-cols-2 gap-x-6 gap-y-10 px-4 py-12 sm:px-5 sm:py-16 md:grid-cols-[1.4fr_repeat(3,1fr)] md:px-8">
        <div className="col-span-2 md:col-span-1">
          <Logo />
          <p className="mt-4 max-w-xs text-[13px] leading-6 text-muted-foreground">
            Controlled security assessments for AI agents. Assessment results are internal evidence, not certification.
          </p>
        </div>
        {groups.map((group) => (
          <div key={group.title}>
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-faint">{group.title}</p>
            <ul className="mt-4 space-y-3 text-[13px]">
              {group.links.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-muted-foreground transition-colors hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mx-auto border-t border-border px-5 py-6 font-mono text-[11px] text-faint md:px-8">
        <span>© 2026 Aegis.</span>
      </div>
    </footer>
  );
}
