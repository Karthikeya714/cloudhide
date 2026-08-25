import type { PropsWithChildren, ReactNode } from "react";

interface CardProps {
  title?: string;
  action?: ReactNode;
  className?: string;
}

export default function Card({
  title,
  action,
  className = "",
  children,
}: PropsWithChildren<CardProps>) {
  return (
    <div
      className={`rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm ${className}`}
    >
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h2 className="text-base font-semibold text-slate-100">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
