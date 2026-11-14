import type { ReactNode } from "react";

export function SectionHeading({
  eyebrow,
  title,
  description,
  action
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow ? (
          <div className="eyebrow">{eyebrow}</div>
        ) : null}
        <h1>{title}</h1>
        {description ? (
          <p className="section-description">{description}</p>
        ) : null}
      </div>
      {action ? <div className="heading-action">{action}</div> : null}
    </div>
  );
}