import { AgentForm } from "@/components/agent-form";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";

export default function NewAgentPage() {
  return (
    <div>
      <PageHeader kicker="Registry" title="Register an agent" description="These details describe the system under test. They do not start an assessment." />
      <Card className="p-5">
        <AgentForm />
      </Card>
    </div>
  );
}
