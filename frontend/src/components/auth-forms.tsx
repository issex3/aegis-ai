"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Field } from "@/components/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { clientApi, fieldErrors } from "@/lib/api";
import type { Session } from "@/lib/types";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [challengeId, setChallengeId] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    if (challengeId) {
      const verified = await clientApi<Session>("/auth/mfa/verify", {
        method: "POST",
        body: JSON.stringify({ challenge_id: challengeId, code: form.get("code") }),
      });
      setPending(false);
      if (!verified.ok) {
        setError(verified.error.error.message);
        return;
      }
      router.push(params.get("next") || "/dashboard");
      router.refresh();
      return;
    }
    const result = await clientApi<Session & { mfa_required?: boolean; challenge_id?: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
    });
    setPending(false);
    if (!result.ok) {
      setError(result.error.error.message);
      return;
    }
    if (result.data.mfa_required && result.data.challenge_id) {
      setChallengeId(result.data.challenge_id);
      return;
    }
    router.push(params.get("next") || "/dashboard");
    router.refresh();
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {challengeId ? (
        <Field label="Authentication code" htmlFor="code" hint="Enter the 6-digit code from your authenticator app, or a recovery code.">
          <Input id="code" name="code" inputMode="numeric" autoComplete="one-time-code" required />
        </Field>
      ) : (
        <>
          <Field label="Email" htmlFor="email">
            <Input id="email" name="email" type="email" autoComplete="email" required />
          </Field>
          <Field label="Password" htmlFor="password">
            <Input id="password" name="password" type="password" autoComplete="current-password" required />
          </Field>
        </>
      )}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Signing in…" : challengeId ? "Verify" : "Sign in"}
      </Button>
      <p className="text-sm text-muted-foreground">
        No account yet? <Link href="/register" className="text-foreground underline underline-offset-4">Create an organisation</Link>
      </p>
      <p className="text-sm text-muted-foreground">
        <Link href="/forgot-password" className="text-foreground underline underline-offset-4">Forgot password</Link>
      </p>
    </form>
  );
}

export function RegisterForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setFields({});
    const form = new FormData(event.currentTarget);
    const result = await clientApi<Session>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: form.get("full_name"),
        email: form.get("email"),
        password: form.get("password"),
        organisation_name: form.get("organisation_name"),
      }),
    });
    setPending(false);
    if (!result.ok) {
      setError(result.error.error.message);
      setFields(fieldErrors(result.error));
      return;
    }
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Field label="Full name" htmlFor="full_name" error={fields.full_name}>
        <Input id="full_name" name="full_name" autoComplete="name" required />
      </Field>
      <Field label="Work email" htmlFor="email" error={fields.email}>
        <Input id="email" name="email" type="email" autoComplete="email" required />
      </Field>
      <Field label="Organisation" htmlFor="organisation_name" error={fields.organisation_name}>
        <Input id="organisation_name" name="organisation_name" required />
      </Field>
      <Field label="Password" htmlFor="password" error={fields.password} hint="At least 12 characters, with a letter and a number.">
        <Input id="password" name="password" type="password" autoComplete="new-password" required minLength={12} />
      </Field>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-sm text-muted-foreground">
        Already registered? <Link href="/login" className="text-foreground underline underline-offset-4">Sign in</Link>
      </p>
    </form>
  );
}

export function ForgotPasswordForm() {
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const result = await clientApi("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email: form.get("email") }),
    });
    setPending(false);
    if (!result.ok) {
      setError(result.error.error.message);
      return;
    }
    setSent(true);
  }

  if (sent) {
    return <p className="text-sm text-muted-foreground">If that email is registered, a reset link has been sent. The link expires in 30 minutes.</p>;
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Field label="Email" htmlFor="email">
        <Input id="email" name="email" type="email" autoComplete="email" required />
      </Field>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Sending…" : "Send reset link"}
      </Button>
      <p className="text-sm text-muted-foreground">
        <Link href="/login" className="text-foreground underline underline-offset-4">Back to sign in</Link>
      </p>
    </form>
  );
}

export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const result = await clientApi("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: form.get("new_password") }),
    });
    setPending(false);
    if (!result.ok) {
      setError(result.error.error.message);
      return;
    }
    router.push("/login");
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Field label="New password" htmlFor="new_password" hint="At least 12 characters, with a letter and a number.">
        <Input id="new_password" name="new_password" type="password" autoComplete="new-password" required minLength={12} />
      </Field>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Updating…" : "Set new password"}
      </Button>
    </form>
  );
}
