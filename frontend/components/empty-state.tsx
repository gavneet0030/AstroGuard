export function EmptyState({
  title,
  description,
  label = "Awaiting verified backend contract"
}: {
  title: string;
  description: string;
  label?: string;
}) {
  return (
    <div className="empty-state">
      <div className="empty-orbit"><span /></div>
      <div className="eyebrow">{label}</div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
