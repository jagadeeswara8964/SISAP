import * as React from "react";
import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { Badge } from "./ui/Badge";
import { ScoreBar } from "./ScoreBar";
import { TypeBadge } from "./TypeBadge";
import { truncate } from "@/utils/cn";
import type { Recommendation } from "@/types";

export interface RecommendationCardProps {
  recommendation: Recommendation;
  defaultOpen?: boolean;
  onSelectStandard?: (standardId: string) => void;
}

/** Expandable recommendation card showing evidence for why a standard matched. */
export function RecommendationCard({
  recommendation,
  defaultOpen = false,
  onSelectStandard,
}: RecommendationCardProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  const panelId = `rec-panel-${recommendation.standard_id.replace(/[^a-zA-Z0-9]/g, "-")}`;
  const validation = recommendation.validation;

  return (
    <article className="rounded border border-ink-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full flex-wrap items-center gap-3 px-3.5 py-3 text-left hover:bg-ink-50/70"
      >
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-ink-400 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
        <div className="min-w-[150px] flex-1">
          <p className="font-mono text-[13px] font-semibold text-navy-900">{recommendation.standard_number}</p>
          <p className="mt-0.5 text-xs leading-snug text-ink-600">{truncate(recommendation.title, 95)}</p>
        </div>
        <div className="flex items-center gap-2">
          <TypeBadge type={recommendation.type} />
        </div>
        <div className="w-28 shrink-0">
          <ScoreBar value={recommendation.score} />
        </div>
        <Badge tone={recommendation.status === "Active" ? "ok" : "crit"}>{recommendation.status}</Badge>
      </button>

      {open && (
        <div id={panelId} className="border-t border-ink-200 px-3.5 py-3.5">
          <div className="grid gap-5 lg:grid-cols-2">
            <div>
              <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Why this standard?
              </h4>
              <ul className="mt-1.5 space-y-1">
                {recommendation.explanation.map((reason, index) => (
                  <li key={index} className="flex gap-2 text-xs leading-relaxed text-ink-800">
                    <span aria-hidden="true" className="mt-0.5 text-ok-500">
                      &#10003;
                    </span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>

              {recommendation.scope && (
                <div className="mt-3">
                  <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">Scope</h4>
                  <p className="mt-1 text-xs leading-relaxed text-ink-600">{recommendation.scope}</p>
                </div>
              )}

              {recommendation.score_breakdown && (
                <div className="mt-3">
                  <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                    Score components
                  </h4>
                  <ul className="mt-1.5 space-y-1">
                    {Object.entries(recommendation.score_breakdown)
                      .filter(([key]) => key !== "weights")
                      .map(([key, value]) => (
                        <li key={key} className="flex items-center justify-between gap-3 text-xs">
                          <span className="text-ink-600">{key.replace(/_/g, " ")}</span>
                          <span className="font-mono text-ink-800">
                            {Number(value).toFixed(2)} &times;{" "}
                            {recommendation.score_breakdown?.weights?.[key] ?? 0}
                          </span>
                        </li>
                      ))}
                  </ul>
                </div>
              )}
            </div>

            <div>
              <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Matched requirements
              </h4>
              {recommendation.matched_requirements.length ? (
                <ul className="mt-1.5 space-y-1">
                  {recommendation.matched_requirements.map((item, index) => (
                    <li key={index} className="flex gap-2 text-xs leading-relaxed text-ink-800">
                      <span aria-hidden="true" className="mt-0.5 text-ok-500">
                        &#10003;
                      </span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-xs text-ink-400 italic">No direct requirement overlap recorded</p>
              )}

              <h4 className="mt-3 text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Requirements not stated in the tender
              </h4>
              {recommendation.missing_requirements.length ? (
                <ul className="mt-1.5 space-y-1">
                  {recommendation.missing_requirements.map((item, index) => (
                    <li key={index} className="flex gap-2 text-xs leading-relaxed text-ink-700">
                      <span aria-hidden="true" className="mt-0.5 text-warn-500">
                        &#8226;
                      </span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-xs text-ink-400 italic">None recorded</p>
              )}
            </div>
          </div>

          {validation && (
            <div className="mt-4 rounded border border-ink-200 bg-ink-50/70 p-3">
              <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                Version / amendment validation
              </h4>
              <ul className="mt-1.5 space-y-1">
                {validation.checks.map((check, index) => (
                  <li key={index} className="font-mono text-[11px] leading-relaxed text-ink-700">
                    {check}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[10px] text-ink-400">Validation source: {validation.validation_source}</p>
            </div>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-ink-100 pt-3">
            {onSelectStandard && (
              <button
                type="button"
                onClick={() => onSelectStandard(recommendation.standard_id)}
                className="text-xs font-semibold text-gov-700 hover:text-gov-800 hover:underline"
              >
                View in standards explorer
              </button>
            )}
            {recommendation.related_standards.length > 0 && (
              <p className="text-[11px] text-ink-500">
                <span className="font-semibold">Related: </span>
                <span className="font-mono">{recommendation.related_standards.join(", ")}</span>
              </p>
            )}
          </div>
        </div>
      )}
    </article>
  );
}

export function RecommendationTableRow({
  recommendation,
  onOpen,
}: {
  recommendation: Recommendation;
  onOpen?: (recommendation: Recommendation) => void;
}) {
  return (
    <tr>
      <td>
        <p className="font-mono text-[13px] font-semibold text-navy-900">{recommendation.standard_number}</p>
        <p className="mt-0.5 max-w-md text-xs text-ink-600">{truncate(recommendation.title, 90)}</p>
      </td>
      <td>
        <TypeBadge type={recommendation.type} />
      </td>
      <td className="w-32">
        <ScoreBar value={recommendation.score} />
      </td>
      <td>
        <Badge tone={recommendation.status === "Active" ? "ok" : "crit"}>{recommendation.status}</Badge>
      </td>
      <td className="max-w-sm text-xs leading-relaxed text-ink-700">
        {recommendation.explanation[0] ?? "Matched on stored standard metadata"}
      </td>
      <td>
        {onOpen && (
          <button
            type="button"
            onClick={() => onOpen(recommendation)}
            className="text-xs font-semibold text-gov-700 hover:underline"
          >
            Details
          </button>
        )}
      </td>
    </tr>
  );
}

export function StandardLink({ id }: { id: string }) {
  return (
    <Link to={`/standards/${encodeURIComponent(id)}`} className="font-mono text-xs text-gov-700 hover:underline">
      {id}
    </Link>
  );
}
