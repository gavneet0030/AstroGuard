import { BrainCircuit, Gauge, Microscope } from "lucide-react";
import { SectionHeading } from "@/components/ui/section-heading";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";

export function ModelWorkspace() {
  return (
    <>
      <SectionHeading
        eyebrow="INTELLIGENCE / MACHINE LEARNING"
        title="Model Observatory"
        description="Monitor inference services, deployed models, and model quality."
      />

      <div className="summary-grid">
        <div className="metric-card">
          <div className="metric-top">
            <span>Registered models</span>
            <BrainCircuit size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">Model endpoint schema pending</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Inference latency</span>
            <Gauge size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">No latency metrics endpoint</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Model quality</span>
            <Microscope size={17} />
          </div>
          <div className="metric-value">—</div>
          <div className="metric-note">No evaluation endpoint</div>
        </div>
      </div>

      <Panel
        title="Model inventory"
        subtitle="Model registry and inference status"
      >
        <EmptyState
          kind="database"
          title="Model inventory integration pending"
          description="A model status and model list route exists in the backend inventory, but its complete response contract and router prefix must be verified before connecting this screen."
        />
      </Panel>
    </>
  );
}