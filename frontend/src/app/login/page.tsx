import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthLayout } from "@/components/auth-layout";
import { LoginForm } from "@/components/auth-forms";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <AuthLayout
      title="Sign in"
      description="Use the email address for your organisation account."
      aside={{
        heading: "Return to your assessment record.",
        points: [
          "Sessions are held on the server and expire automatically.",
          "Passwords are hashed with Argon2id.",
          "Agent credentials are never returned to the browser.",
        ],
      }}
    >
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
