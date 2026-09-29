import * as React from "react";
import { Link } from "react-router-dom";
import { FileBarChart2, FileText } from "lucide-react";
import { api, ApiError, reportDownloadUrl } from "@/services/api";
import { useToast } from "@/components/ui/Toast";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { truncate } from "@/utils/cn";
import type { RecentAnalysis } from "@/types";

const REPORT_SECTIONS = [
  "Executive Summary",
  "Document Information",
  "Extracted Requirements",
  "Recommended Standards",
  "Relevance Reasons",
  "Related Standards",
  "Version and Amendment Validation",
  "Certification Information",
  "Potential Specification Gaps",
  "Standards Relationship Graph",
  "Review Notes",
  "Data Sources",
];

export default function ReportsPage() {
  const { push } = useToast();
  const [rows, setRows] = React.useState<RecentAnalysis[] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [busyId, setBusyId] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .dashboard()
      .then((stats) => {
        if (!cancelled) setRows(stats.recent_analyses);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load documents.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const generate = async (documentId: string) => {
    setBusyId(documentId);
    try {
      const report = await api.report(documentId);
      window.open(reportDownloadUrl(report.download_url), "_blank", "noopener,noreferrer");
      push({
        tone: "success",
        title: "Report generated",
        description: `${report.report_id} - the PDF has opened in a new tab.`,
      });
    } catch (err: unknown) {
      push({
        tone: "error",
        title: "Report generation failed",
        description: err instanceof ApiError ? err.message : "Unexpected error.",
      });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-navy-900 sm:text-2xl">Reports</h1>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-ink-600">
          Generate a professional procurement analysis report for any analysed document. Reports are
          exported as PDF and contain the full evidence trail behind each recommendation.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Report contents</CardTitle>
          <CardDescription>Every report includes these 12 sections</CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {REPORT_SECTIONS.map((section, index) => (
              <li key={section} className="flex items-start gap-2 text-xs text-ink-700">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded bg-gov-50 font-mono text-[9px] font-bold text-gov-700">
                  {index + 1}
                </span>
                {section}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded border border-crit-100 bg-crit-50 px-4 py-3 text-sm text-crit-700">{error}</div>
      )}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-20 w-full" />
          ))}
        </div>
      ) : !rows || rows.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={<FileBarChart2 className="h-8 w-8" />}
              title="No documents to report on"
              description="Analyse a tender first, then return here to generate its PDF report."
              action={
                <Link to="/analyze">
                  <Button>
                    <FileText className="h-4 w-4" aria-hidden="true" />
                    Analyze a tender
                  </Button>
                </Link>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {rows.map((row) => (
            <Card key={row.document_id}>
              <CardContent className="flex h-full flex-col pt-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-navy-900">{row.filename}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-ink-400">{row.document_id}</p>
                  </div>
                  <Badge tone={row.status === "Standards identified" ? "ok" : "warn"}>{row.status}</Badge>
                </div>
                <p className="mt-2 text-xs text-ink-600">
                  {truncate(row.product, 70)} &middot; {row.standards} standards &middot; {row.gaps} potential gaps
                </p>
                <p className="mt-0.5 text-[11px] text-ink-400">Analysed {row.date}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => generate(row.document_id)} loading={busyId === row.document_id}>
                    <FileBarChart2 className="h-4 w-4" aria-hidden="true" />
                    Generate PDF report
                  </Button>
                  <Link to={`/analyze/${row.document_id}/recommendations`}>
                    <Button size="sm" variant="outline">
                      View recommendations
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <p className="rounded border border-warn-100 bg-warn-50 px-3 py-2 text-[11px] leading-relaxed text-warn-700">
        Reports are generated from the curated demo dataset and are not verified against the live BIS
        catalogue. AI-generated recommendations should be reviewed by the responsible procurement/technical
        authority.
      </p>
    </div>
  );
}
