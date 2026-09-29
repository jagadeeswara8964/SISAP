import * as React from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  FileBarChart2,
  Filter,
  Loader2,
  Network,
  Search,
  TriangleAlert,
} from "lucide-react";
import { api, ApiError, reportDownloadUrl } from "@/services/api";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input, Select } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { ConfidenceChart } from "@/components/ConfidenceChart";
import { GapsPanel } from "@/components/GapsPanel";
import { StandardsGraph } from "@/components/StandardsGraph";
import { RecommendationCard, RecommendationTableRow } from "@/components/RecommendationCard";
import { Modal } from "@/components/ui/Modal";
import type { GraphNode, Recommendation, RecommendationResponse, RequirementObject } from "@/types";

const TYPE_ORDER = ["Primary", "Testing", "Safety", "Installation", "Terminology", "Reference", "Related"];
const SORTS = [
  { id: "relevance", label: "Relevance (high to low)" },
  { id: "standard", label: "Standard number" },
  { id: "type", label: "Standard type" },
] as const;

export default function RecommendationsPage() {
  const { documentId = "" } = useParams();
  const { push } = useToast();

  const [data, setData] = React.useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [graph, setGraph] = React.useState<{ nodes: GraphNode[]; edges: { source: string; target: string; relationship: string }[] }>({
    nodes: [],
    edges: [],
  });
  const [graphLoading, setGraphLoading] = React.useState(false);

  // filters
  const [query, setQuery] = React.useState("");
  const [typeFilter, setTypeFilter] = React.useState("");
  const [categoryFilter, setCategoryFilter] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("");
  const [minScore, setMinScore] = React.useState(0);
  const [sort, setSort] = React.useState<(typeof SORTS)[number]["id"]>("relevance");
  const [view, setView] = React.useState<"cards" | "table">("cards");
  const [selected, setSelected] = React.useState<Recommendation | null>(null);
  const [reporting, setReporting] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .recommendations(documentId)
      .then((result) => {
        if (!cancelled) {
          setData(result);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load recommendations.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  // Build the relationship graph from the top primary standard.
  React.useEffect(() => {
    if (!data) return;
    const primary = data.recommendations.find((rec) => rec.type === "Primary");
    if (!primary) return;

    setGraphLoading(true);
    const scores: Record<string, number> = {};
    const types: Record<string, string> = {};
    data.recommendations.forEach((rec) => {
      scores[rec.standard_id] = rec.score;
      types[rec.standard_id] = rec.type;
    });

    api
      .standardGraph(primary.standard_id, 1)
      .then((payload) => {
        const nodes = payload.nodes.map((node) => ({
          ...node,
          score: scores[node.id] ?? node.score,
          node_type: types[node.id] ?? node.node_type,
        }));
        // Recommended standards not already in the graph payload are appended so
        // the visualisation covers the whole recommendation set.
        const known = new Set(nodes.map((node) => node.id));
        const extra: GraphNode[] = data.recommendations
          .filter((rec) => !known.has(rec.standard_id))
          .slice(0, 10)
          .map((rec) => ({
            id: rec.standard_id,
            label: rec.standard_number,
            title: rec.title,
            node_type: rec.type,
            relationship: "related",
            version: rec.version ?? "",
            status: rec.status,
            score: rec.score,
            is_root: false,
          }));
        setGraph({ nodes: [...nodes, ...extra], edges: payload.edges });
      })
      .catch(() => setGraph({ nodes: [], edges: [] }))
      .finally(() => setGraphLoading(false));
  }, [data]);

  const categories = React.useMemo(
    () => [...new Set((data?.recommendations ?? []).map((rec) => rec.category))].sort(),
    [data],
  );

  const filtered = React.useMemo(() => {
    const needle = query.trim().toLowerCase();
    let list = (data?.recommendations ?? []).filter((rec) => {
      if (typeFilter && rec.type !== typeFilter) return false;
      if (categoryFilter && rec.category !== categoryFilter) return false;
      if (statusFilter && rec.status !== statusFilter) return false;
      if (rec.score < minScore) return false;
      if (!needle) return true;
      return (
        rec.standard_id.toLowerCase().includes(needle) ||
        rec.standard_number.toLowerCase().includes(needle) ||
        rec.title.toLowerCase().includes(needle) ||
        rec.explanation.some((reason) => reason.toLowerCase().includes(needle))
      );
    });

    list = [...list].sort((a, b) => {
      if (sort === "standard") return a.standard_number.localeCompare(b.standard_number);
      if (sort === "type") return TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type) || b.score - a.score;
      return b.score - a.score;
    });
    return list;
  }, [data, query, typeFilter, categoryFilter, statusFilter, minScore, sort]);

  const generateReport = async () => {
    setReporting(true);
    try {
      const report = await api.report(documentId);
      window.open(reportDownloadUrl(report.download_url), "_blank", "noopener,noreferrer");
      push({
        tone: "success",
        title: "Report generated",
        description: `${report.report_id} - ${report.sections.length} sections. The PDF has opened in a new tab.`,
      });
    } catch (err: unknown) {
      push({
        tone: "error",
        title: "Report generation failed",
        description: err instanceof ApiError ? err.message : "Unexpected error.",
      });
    } finally {
      setReporting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-20 w-full" />
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent>
          <EmptyState
            icon={<TriangleAlert className="h-8 w-8" />}
            title="Recommendations unavailable"
            description={
              error ??
              "No sufficiently relevant standard was found in the current curated dataset. Consider expanding the standards database or reviewing the specification manually."
            }
            action={
              <Link to="/analyze">
                <Button variant="outline">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  Back to analyze
                </Button>
              </Link>
            }
          />
        </CardContent>
      </Card>
    );
  }

  const summary = data.summary;
  const noResults = filtered.length === 0 && data.recommendations.length > 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/analyze" className="inline-flex items-center gap-1.5 text-xs font-medium text-gov-700 hover:underline">
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Analyze another tender
          </Link>
          <h1 className="mt-1.5 text-xl font-bold tracking-tight text-navy-900 sm:text-2xl">
            Applicable Indian Standards
          </h1>
          <p className="mt-1 text-sm text-ink-600">
            {data.product ? (
              <>
                Product: <span className="font-medium text-ink-800">{data.product}</span>
                {data.category && <> &middot; Category: <span className="font-medium text-ink-800">{data.category}</span></>}
              </>
            ) : (
              "Analysis result"
            )}{" "}
            &middot; Document <span className="font-mono text-xs">{data.document_id}</span>
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={generateReport} loading={reporting}>
            <FileBarChart2 className="h-4 w-4" aria-hidden="true" />
            Generate PDF report
          </Button>
        </div>
      </div>

      {/* Summary strip */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryTile label="Standards identified" value={summary.total} hint={`${summary.high_relevance} high relevance`} />
        <SummaryTile label="Primary standards" value={summary.primary} hint="Directly applicable to the product" tone="gov" />
        <SummaryTile
          label="Testing / safety"
          value={summary.testing + summary.safety}
          hint={`${summary.testing} testing, ${summary.safety} safety`}
          tone="warn"
        />
        <SummaryTile label="Potential gaps" value={summary.potential_gaps} hint="Require officer review" tone="crit" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          {/* Filters */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-ink-400" aria-hidden="true" />
                  Filter and sort
                </CardTitle>
                <div className="flex gap-1" role="tablist" aria-label="Result view">
                  {(["cards", "table"] as const).map((option) => (
                    <button
                      key={option}
                      role="tab"
                      aria-selected={view === option}
                      onClick={() => setView(option)}
                      className={`rounded px-2.5 py-1 text-xs font-medium ${
                        view === option ? "bg-navy-900 text-white" : "bg-ink-100 text-ink-600 hover:bg-ink-200"
                      }`}
                    >
                      {option === "cards" ? "Detailed cards" : "Table"}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div className="relative sm:col-span-2 lg:col-span-1">
                  <Search className="pointer-events-none absolute top-2.5 left-2.5 h-3.5 w-3.5 text-ink-400" aria-hidden="true" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search standards"
                    className="pl-8"
                    aria-label="Search standards"
                  />
                </div>
                <Select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} aria-label="Filter by type">
                  <option value="">All types</option>
                  {TYPE_ORDER.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </Select>
                <Select
                  value={categoryFilter}
                  onChange={(event) => setCategoryFilter(event.target.value)}
                  aria-label="Filter by category"
                >
                  <option value="">All categories</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </Select>
                <Select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  aria-label="Filter by status"
                >
                  <option value="">Any status</option>
                  <option value="Active">Active</option>
                  <option value="Superseded">Superseded</option>
                </Select>
                <div className="flex items-center gap-2">
                  <Input
                    type="range"
                    min={0}
                    max={90}
                    step={5}
                    value={minScore}
                    onChange={(event) => setMinScore(Number(event.target.value))}
                    className="h-9 px-0"
                    aria-label="Minimum relevance score"
                  />
                  <span className="w-14 shrink-0 font-mono text-xs text-ink-600">&ge; {minScore}</span>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-ink-500">
                  Showing <span className="font-semibold text-ink-800">{filtered.length}</span> of {data.recommendations.length} standards
                </p>
                <Select value={sort} onChange={(event) => setSort(event.target.value as typeof sort)} aria-label="Sort results" className="h-8 w-auto text-xs">
                  {SORTS.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          {noResults ? (
            <Card>
              <CardContent>
                <EmptyState
                  icon={<Search className="h-8 w-8" />}
                  title="No standards match the current filters"
                  description="Try widening the relevance threshold or clearing the type/category filters."
                  action={
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setQuery("");
                        setTypeFilter("");
                        setCategoryFilter("");
                        setStatusFilter("");
                        setMinScore(0);
                      }}
                    >
                      Reset filters
                    </Button>
                  }
                />
              </CardContent>
            </Card>
          ) : view === "cards" ? (
            <div className="space-y-2.5">
              {filtered.map((rec, index) => (
                <RecommendationCard
                  key={rec.standard_id}
                  recommendation={rec}
                  defaultOpen={index === 0}
                  onSelectStandard={() => setSelected(rec)}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="px-0 py-0">
                <div className="overflow-x-auto">
                  <table className="sisap-table">
                    <thead>
                      <tr>
                        <th>Standard</th>
                        <th>Type</th>
                        <th>Relevance</th>
                        <th>Status</th>
                        <th>Reason</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((rec) => (
                        <RecommendationTableRow key={rec.standard_id} recommendation={rec} onOpen={setSelected} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <ConfidenceChart recommendations={data.recommendations} />
          <GapsPanel gaps={data.gaps} reviewNote={data.review_note} />

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-4 w-4 text-ink-400" aria-hidden="true" />
                Standards relationship graph
              </CardTitle>
              <CardDescription>Primary standard and its testing, safety and reference links</CardDescription>
            </CardHeader>
            <CardContent>
              <StandardsGraph
                nodes={graph.nodes}
                edges={graph.edges}
                loading={graphLoading}
                onSelect={(node) => {
                  const rec = data.recommendations.find((item) => item.standard_id === node.id);
                  if (rec) setSelected(rec);
                }}
              />
            </CardContent>
          </Card>

          <ExtractedRequirementsCard documentId={documentId} />
        </div>
      </div>

      {/* Detail modal */}
      <Modal
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected ? selected.standard_number : ""}
        description={selected?.title}
        size="lg"
      >
        {selected && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="primary">{selected.type}</Badge>
              <Badge tone={selected.status === "Active" ? "ok" : "crit"}>{selected.status}</Badge>
              <Badge tone="neutral">Relevance {Math.round(selected.score)}</Badge>
              {selected.version && <Badge tone="neutral">v{selected.version}</Badge>}
            </div>

            {selected.scope && (
              <div>
                <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">Scope</h4>
                <p className="mt-1 text-xs leading-relaxed text-ink-700">{selected.scope}</p>
              </div>
            )}

            <div>
              <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">Why recommended</h4>
              <ul className="mt-1.5 space-y-1">
                {selected.explanation.map((reason, index) => (
                  <li key={index} className="flex gap-2 text-xs leading-relaxed text-ink-800">
                    <span aria-hidden="true" className="mt-0.5 text-ok-500">&#10003;</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">Matched requirements</h4>
                <ul className="mt-1.5 space-y-1">
                  {selected.matched_requirements.length ? (
                    selected.matched_requirements.map((item, index) => (
                      <li key={index} className="text-xs leading-relaxed text-ink-800">&#10003; {item}</li>
                    ))
                  ) : (
                    <li className="text-xs text-ink-400 italic">None recorded</li>
                  )}
                </ul>
              </div>
              <div>
                <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">Missing requirements</h4>
                <ul className="mt-1.5 space-y-1">
                  {selected.missing_requirements.length ? (
                    selected.missing_requirements.map((item, index) => (
                      <li key={index} className="text-xs leading-relaxed text-ink-700">&#8226; {item}</li>
                    ))
                  ) : (
                    <li className="text-xs text-ink-400 italic">None recorded</li>
                  )}
                </ul>
              </div>
            </div>

            {selected.validation && (
              <div className="rounded border border-ink-200 bg-ink-50/70 p-3">
                <h4 className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                  Version / amendment validation
                </h4>
                <ul className="mt-1.5 space-y-1">
                  {selected.validation.checks.map((check, index) => (
                    <li key={index} className="font-mono text-[11px] text-ink-700">{check}</li>
                  ))}
                </ul>
                <p className="mt-2 text-[10px] text-ink-400">
                  Validation source: {selected.validation.validation_source}
                </p>
              </div>
            )}

            <div className="flex flex-wrap gap-2 border-t border-ink-100 pt-3">
              <Link to={`/standards/${encodeURIComponent(selected.standard_id)}`}>
                <Button variant="outline" size="sm">
                  Open in standards explorer
                </Button>
              </Link>
              {selected.related_standards.length > 0 && (
                <p className="self-center text-[11px] text-ink-500">
                  Related: <span className="font-mono">{selected.related_standards.join(", ")}</span>
                </p>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Floating progress hint during report generation */}
      {reporting && (
        <div className="fixed inset-x-0 bottom-4 z-30 mx-auto flex w-fit items-center gap-2 rounded bg-navy-900 px-4 py-2 text-xs text-white shadow-lg">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          Generating report...
        </div>
      )}
    </div>
  );
}

function ExtractedRequirementsCard({ documentId }: { documentId: string }) {
  const [requirements, setRequirements] = React.useState<RequirementObject | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    api
      .document(documentId)
      .then((doc) => {
        if (!cancelled) setRequirements(doc.requirements ?? null);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Extracted requirements</CardTitle>
        <CardDescription>As understood from the uploaded document</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-4 w-full" />
            ))}
          </div>
        ) : !requirements ? (
          <p className="text-xs text-ink-400">Requirements are not available for this document.</p>
        ) : (
          <dl className="space-y-2 text-xs">
            {(
              [
                ["Product", requirements.product],
                ["Category", requirements.category],
                ["Intended use", requirements.intended_use],
                ["Materials", requirements.materials.join(", ")],
                ["Technical", requirements.technical_requirements.length + " clauses"],
                ["Performance", requirements.performance_requirements.length + " clauses"],
                ["Safety", requirements.safety_requirements.length + " clauses"],
                ["Testing", requirements.testing_requirements.length + " clauses"],
                ["Installation", requirements.installation_requirements.length + " clauses"],
                ["Certification", requirements.certification_requirements.length + " clauses"],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="flex items-baseline justify-between gap-3 border-b border-ink-100 pb-1.5 last:border-0">
                <dt className="shrink-0 text-ink-500">{label}</dt>
                <dd className="text-right font-medium text-ink-800">
                  {value || <span className="font-normal text-ink-400 italic">Not stated</span>}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryTile({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: number;
  hint: string;
  tone?: "neutral" | "gov" | "warn" | "crit";
}) {
  const toneClass =
    tone === "gov" ? "text-gov-600" : tone === "warn" ? "text-warn-500" : tone === "crit" ? "text-crit-500" : "text-navy-900";
  return (
    <Card>
      <CardContent className="pt-4">
        <p className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">{label}</p>
        <p className={`mt-1.5 font-mono text-2xl font-bold tabular-nums ${toneClass}`}>{value}</p>
        <p className="mt-0.5 text-[11px] text-ink-400">{hint}</p>
      </CardContent>
    </Card>
  );
}
