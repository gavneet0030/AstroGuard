import { Database, Radio, ShieldAlert } from "lucide-react";

export function EmptyState({
  title,
  description,
  kind = "database"
}: {
  title: string;
  description: string;
  kind?: "database" | "telemetry" | "security";
}) {
  const Icon =
    kind === "telemetry"
      ? Radio
      : kind === "security"
        ? ShieldAlert
        : Database;

  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Icon size={22} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}