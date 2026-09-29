import { cn, percent } from "@/utils/cn";

export interface ScoreBarProps {
  value: number;
  className?: string;
  compact?: boolean;
}

/** Inline relevance score bar used in tables and cards. */
export function ScoreBar({ value, className, compact = false }: ScoreBarProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const tone = clamped >= 70 ? "bg-ok-500" : clamped >= 45 ? "bg-gov-600" : clamped >= 25 ? "bg-warn-500" : "bg-crit-500";
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="h-1.5 w-full min-w-[52px] overflow-hidden rounded-full bg-ink-200"
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Relevance ${percent(clamped)}`}
      >
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${clamped}%` }} />
      </div>
      {!compact && <span className="w-9 shrink-0 text-right font-mono text-xs text-ink-600">{Math.round(clamped)}</span>}
    </div>
  );
}
