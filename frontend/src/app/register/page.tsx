import type { Metadata } from "next";
import { AuthLayout } from "@/components/auth-layout";
import { RegisterForm } from "@/components/auth-forms";

export const metadata: Metadata = { title: "Create an organisation" };

export default function RegisterPage() {
  return (
    <AuthLayout
      title="Create an organisation"
      description="The first account becomes the organisation owner. You can rename the organisation later."
      aside={{
        heading: "Start with the demonstration agent. No API key required.",
        points: [
          "Registration creates your user, an organisation, and an owner membership.",
          "Industry scenario libraries for customer service, accounting, healthcare, legal, and sales.",
          "Demonstration results are labelled as simulated throughout.",
        ],
      }}
    >
      <RegisterForm />
    </AuthLayout>
  );
}
