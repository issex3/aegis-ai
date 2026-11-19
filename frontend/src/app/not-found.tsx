import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6">
      <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">404</p>
      <h1 className="mt-2 text-2xl font-semibold">This page is not available</h1>
      <p className="mt-2 text-sm text-muted-foreground">The record may belong to another organisation, or the address is wrong.</p>
      <Link href="/dashboard" className="mt-6 text-sm underline underline-offset-4">
        Back to the dashboard
      </Link>
    </div>
  );
}
