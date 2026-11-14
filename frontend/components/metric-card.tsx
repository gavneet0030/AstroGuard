type Props = {
  label: string;
  value: string;
  detail: string;
  icon: string;
};

export function MetricCard({ label, value, detail, icon }: Props) {
  return (
    <article className="metric-card">
      <div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}
