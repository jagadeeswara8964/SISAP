import * as React from "react";
import { cn } from "@/utils/cn";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-12 text-center", className)}>
      {icon && <div className="mb-3 text-ink-300">{icon}</div>}
      <p className="text-sm font-semibold text-navy-900">{title}</p>
      {description && <p className="mt-1.5 max-w-md text-xs leading-relaxed text-ink-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
