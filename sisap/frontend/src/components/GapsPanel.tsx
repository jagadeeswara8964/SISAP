import { ShieldQuestion } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/Card";
import { Badge } from "./ui/Badge";
import { SeverityBadge } from "./SeverityBadge";
import type { Gap } from "@/types";

export interface GapsPanelProps {
  gaps: Gap[];
  reviewNote?: string;
}

/** Specification gap summary and detail (spec section 15). */
export function GapsPanel({ gaps, reviewNote }: GapsPanelProps) {
  const counts = gaps.reduce<Record<string, number>>((acc, gap) => {
    acc[gap.severity] = (acc[gap.severity] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Potential Specification Gaps</CardTitle>
        <Badge tone={counts.Critical ? "crit" : counts.High ? "warn" : "gov"}>{gaps.length} found</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {(["Critical", "High", "Medium", "Low"] as const).map((severity) => (
            <span key={severity} className="flex items-center gap-1.5">
              <SeverityBadge severity={severity} />
              <span className="font-mono text-xs text-ink-600">{counts[severity] ?? 0}</span>
            </span>
          ))}
        </div>

        {gaps.length === 0 ? (
          <div className="flex flex-col items-center py-6 text-center">
            <ShieldQuestion className="mb-2 h-7 w-7 text-ink-300" aria-hidden="true" />
            <p className="text-sm font-medium text-ink-600">No gaps detected</p>
            <p className="mt-1 max-w-sm text-xs text-ink-400">
              This does not mean the tender is compliant - review by the responsible authority is still
              required.
            </p>
          </div>
        ) : (
          <ul className="space-y-2.5">
            {gaps.map((gap, index) => (
              <li key={index} className="rounded border border-ink-200 bg-white px-3 py-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={gap.severity} />
                  <span className="text-[13px] font-semibold text-navy-900">{gap.gap_type}</span>
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-ink-700">{gap.description}</p>
                <p className="mt-1.5 text-xs leading-relaxed text-ink-600">
                  <span className="font-semibold text-ink-700">Suggested action: </span>
                  {gap.suggested_action}
                </p>
                {gap.related_standards.length > 0 && (
                  <p className="mt-1.5 font-mono text-[11px] text-ink-400">
                    Related: {gap.related_standards.join(", ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}

        <p className="border-t border-ink-100 pt-2.5 text-[11px] leading-relaxed text-ink-500">
          {reviewNote ??
            "Potential gaps requiring procurement officer review. SISAP does not declare a tender legally compliant or non-compliant."}
        </p>
      </CardContent>
    </Card>
  );
}
