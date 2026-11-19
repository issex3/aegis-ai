import { AppShell } from "@/components/app-shell";
import { serverApi } from "@/lib/api";
import type { Session } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const session = await serverApi<Session>("/auth/me");
  return <AppShell session={session}>{children}</AppShell>;
}
