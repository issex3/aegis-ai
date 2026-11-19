import { redirect } from "next/navigation";
import type { ApiErrorBody } from "@/lib/types";

const internalBase = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

export class ApiNotFound extends Error {
  constructor() {
    super("not_found");
  }
}

export async function serverApi<T>(path: string): Promise<T> {
  const { cookies } = await import("next/headers");
  const jar = await cookies();
  const response = await fetch(`${internalBase}/api/v1${path}`, {
    headers: { cookie: jar.toString() },
    cache: "no-store",
  });
  if (response.status === 401) {
    redirect("/login");
  }
  if (response.status === 404) {
    throw new ApiNotFound();
  }
  if (!response.ok) {
    throw new Error("The application could not load this page.");
  }
  return response.json() as Promise<T>;
}

export async function clientApi<T>(path: string, init?: RequestInit): Promise<{ ok: true; data: T } | { ok: false; error: ApiErrorBody }> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Aegis-Client": "web",
      ...(init?.headers ?? {}),
    },
    credentials: "same-origin",
  });
  const data = (await response.json().catch(() => null)) as T | ApiErrorBody | null;
  if (!response.ok) {
    return {
      ok: false,
      error: (data as ApiErrorBody) ?? { error: { code: "request_failed", message: "The request could not be completed." } },
    };
  }
  return { ok: true, data: data as T };
}

export function fieldErrors(error: ApiErrorBody) {
  const map: Record<string, string> = {};
  for (const detail of error.error.details ?? []) {
    map[detail.field] = detail.message;
  }
  return map;
}
