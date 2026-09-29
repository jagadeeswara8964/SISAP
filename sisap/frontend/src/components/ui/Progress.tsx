import { cn } from "@/utils/cn";

const TONES = {
  ok: "bg-ok-500",
  gov: "bg-gov-600",
  warn: "bg-warn-500",
  crit: "bg-crit-500",
} as const;

export interface ProgressProps {
  value: number;
  tone?: keyof typeof TONES;
  label?: string;
  showValue?: boolean;
  className?: string;
}

/** Horizontal progress bar with an accessible label. */
export function Progress({ value, tone = "gov", label, showValue = true, className }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("w-full", className)}>
      {(label || showValue) && (
        <div className="mb-1 flex items-baseline justify-between gap-2">
          {label && <span className="text-xs font-medium text-ink-600">{label}</span>}
          {showValue && <span className="font-mono text-xs text-ink-500">{Math.round(clamped)}%</span>}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "Progress"}
        className="h-2 w-full overflow-hidden rounded-full bg-ink-200"
      >
        <div className={cn("h-full rounded-full transition-all", TONES[tone])} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}
