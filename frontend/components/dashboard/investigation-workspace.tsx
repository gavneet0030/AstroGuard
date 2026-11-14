import { Search, FileSearch, GitBranch } from "lucide-react";
import { SectionHeading } from "@/components/ui/section-heading";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";

export function InvestigationWorkspace() {
  return (
    <>
      <SectionHeading
        eyebrow="INTELLIGENCE / RESPONSE"
        title="Investigation Workspace"
        description="A structured workspace for triage, evidence, and incident analysis."
      />

      <div className="summary-grid">
        <div className="metric-card">
          <div className="metric-top">
            <span>Investigations</span>
            <Search size={17} />
          </div>
          <div className="metric-value">â€”</div>
          <div className="metric-note">Backend integration pending</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Evidence records</span>
            <FileSearch size={17} />
          </div>
          <div className="metric-value">â€”</div>
          <div className="metric-note">Backend integration pending</div>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Correlations</span>
            <GitBranch size={17} />
          </div>
          <div className="metric-value">â€”</div>
          <div className="metric-note">Backend integration pending</div>
        </div>
      </div>

      <Panel
        title="Investigation queue"
        subtitle="Cases and associated evidence"
      >
        <EmptyState
          kind="security"
          title="Investigation service not connected"
          description="The current verified route inventory does not contain investigation CRUD or search endpoints."
        />
      </Panel>
    </>
  );
}
