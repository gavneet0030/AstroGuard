import { Clock3 } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";

export function ActivityPanel() {
  return (
    <Panel
      title="Recent platform activity"
      subtitle="Events and operational changes"
      action={
        <span className="panel-tag">LIVE DATA PENDING</span>
      }
    >
      <EmptyState
        kind="telemetry"
        title="No live activity feed connected"
        description="The current backend audit does not establish an activity-feed endpoint. Activity will appear here once the API contract is implemented and verified."
      />
      <div className="activity-footnote">
        <Clock3 size={13} />
        No synthetic activity is being presented as real data.
      </div>
    </Panel>
  );
}