import { NextRequest, NextResponse } from "next/server";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const params = await context.params;
  const target = `${process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000"}/api/v1/${params.path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  const forwarded = request.headers.get("x-forwarded-for");
  const realIp = request.headers.get("x-real-ip");
  if (!forwarded && realIp) {
    headers.set("x-forwarded-for", realIp);
  }
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    redirect: "manual",
  });
  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const lowered = key.toLowerCase();
    if (lowered === "set-cookie" || lowered === "content-encoding" || lowered === "content-length") return;
    responseHeaders.set(key, value);
  });
  for (const cookie of upstream.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }
  return new NextResponse(await upstream.arrayBuffer(), { status: upstream.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
