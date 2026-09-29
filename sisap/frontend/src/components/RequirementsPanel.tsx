import { AlertTriangle, ClipboardList } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/Card";
import { SkeletonText } from "./ui/Skeleton";
import { Badge } from "./ui/Badge";
import type { RequirementObject } from "@/types";

const SECTIONS: { key: keyof RequirementObject; label: string; list?: boolean }[] = [
  { key: "product", label: "Product" },
  { key: "category", label: "Category" },
  { key: "intended_use", label: "Intended use" },
  { key: "materials", label: "Materials", list: true },
  { key: "technical_requirements", label: "Technical requirements", list: true },
  { key: "performance_requirements", label: "Performance requirements", list: true },
  { key: "safety_requirements", label: "Safety requirements", list: true },
  { key: "testing_requirements", label: "Testing requirements", list: true },
  { key: "installation_requirements", label: "Installation requirements", list: true },
  { key: "certification_requirements", label: "Certification requirements", list: true },
];

export interface RequirementsPanelProps {
  requirements: RequirementObject | null;
  method?: string;
  loading?: boolean;
}

/** Structured view of the requirements extracted from a tender. */
export function RequirementsPanel({ requirements, method, loading = false }: RequirementsPanelProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Extracted Requirements</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index}>
              <SkeletonText lines={2} />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!requirements) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Extracted Requirements</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center py-8 text-center">
            <ClipboardList className="mb-2 h-7 w-7 text-ink-300" aria-hidden="true" />
            <p className="text-sm font-medium text-ink-600">No requirements extracted yet</p>
            <p className="mt-1 max-w-xs text-xs text-ink-400">
              Upload a tender PDF or paste a specification, then run the analysis.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const emptyCount = SECTIONS.filter((section) => {
    const value = requirements[section.key];
    return section.list ? !Array.isArray(value) || value.length === 0 : !value;
  }).length;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Extracted Requirements</CardTitle>
        {method && <Badge tone="neutral">{method}</Badge>}
      </CardHeader>
      <CardContent className="space-y-4">
        {SECTIONS.map((section) => {
          const value = requirements[section.key];
          if (section.list) {
            const items = Array.isArray(value) ? (value as string[]) : [];
            return (
              <div key={String(section.key)}>
                <p className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                  {section.label}
                </p>
                {items.length ? (
                  <ul className="mt-1.5 space-y-1">
                    {items.map((item, index) => (
                      <li key={index} className="flex gap-2 text-[13px] leading-relaxed text-ink-800">
                        <span aria-hidden="true" className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-gov-500" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-xs text-ink-400 italic">Not stated in the document</p>
                )}
              </div>
            );
          }
          return (
            <div key={String(section.key)}>
              <p className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">{section.label}</p>
              <p className="mt-1 text-[13px] font-medium text-ink-900">
                {(value as string) || <span className="font-normal text-ink-400 italic">Not stated</span>}
              </p>
            </div>
          );
        })}

        {emptyCount > 3 && (
          <div className="flex items-start gap-2 rounded border border-warn-100 bg-warn-50 px-3 py-2.5">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warn-500" aria-hidden="true" />
            <p className="text-xs leading-relaxed text-warn-700">
              {emptyCount} requirement categories are not stated in this document. See the specification
              gap analysis for the recommended follow-up actions.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
