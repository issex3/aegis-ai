import type { Metadata } from "next";
import { AuthLayout } from "@/components/auth-layout";
import { ForgotPasswordForm } from "@/components/auth-forms";

export const metadata: Metadata = { title: "Reset password" };

export default function ForgotPasswordPage() {
  return (
    <AuthLayout
      title="Reset password"
      description="We will send a single-use link if the email belongs to an account. The response is the same whether or not the account exists."
      aside={{
        heading: "Password reset is time-limited.",
        points: [
          "Reset tokens expire after 30 minutes and can be used once.",
          "Completing a reset signs out every other session for that account.",
          "If SMTP is not configured, operators must not invent an ad hoc reset.",
        ],
      }}
    >
      <ForgotPasswordForm />
    </AuthLayout>
  );
}
