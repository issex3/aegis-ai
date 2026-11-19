import type { Metadata } from "next";
import { AuthLayout } from "@/components/auth-layout";
import { ResetPasswordForm } from "@/components/auth-forms";

export const metadata: Metadata = { title: "Choose a new password" };

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const params = await searchParams;
  const token = params.token || "";
  return (
    <AuthLayout
      title="Choose a new password"
      description="Use the link from the reset email. Tokens expire after 30 minutes."
      aside={{
        heading: "This replaces the previous password.",
        points: [
          "The previous password stops working immediately.",
          "Existing sessions for the account are revoked.",
          "Sign in again after the password is changed.",
        ],
      }}
    >
      {token ? <ResetPasswordForm token={token} /> : <p className="text-sm text-muted-foreground">This reset link is missing a token.</p>}
    </AuthLayout>
  );
}
