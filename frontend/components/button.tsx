import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  tone?: "primary" | "quiet" | "danger";
};

export function Button({ children, tone = "quiet", className = "", ...props }: Props) {
  return (
    <button className={`button button-${tone} ${className}`} {...props}>
      {children}
    </button>
  );
}
