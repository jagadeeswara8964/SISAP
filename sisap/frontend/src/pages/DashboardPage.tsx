import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookMarked,
  ClipboardList,
  Database,
  FileBarChart2,
  ScanSearch,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { api } from "@/services/api";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { SkeletonCard, Skeleton } from "@/components/ui/Skeleton";
import { Progress } from "@/components/ui/Progress";
import { EmptyState } from "@/components/ui/EmptyState";

export default function DashboardPage() {
  const { data, loading, error } = useApi(() => api.dashboard(), []);
  const { data: health } = useApi(() => api.health(), []);

  const cards = [
    {
      label: "Documents analysed",
      value: data?.documents_analyzed ?? 0,
      icon: ClipboardList,
      tone: "text-gov-600",
      hint: "Tenders processed by SISAP",
    },
    {
      label: "Standards recommended",
      value: data?.standards_recommended ?? 0,
      icon: BookMarked,
      tone: "text-navy-700",
      hint: "Applicable standards identified",
    },
    {
      label: "Potential gaps found",
      value: data?.potential_gaps_found ?? 0,
      icon: TriangleAlert,
      tone: "text-warn-500",
      hint: "Items requiring officer review",
    },
    {
      label: "Validated references",
      value: data?.validated_references ?? 0,
      icon: ShieldCheck,
      tone: "text-ok-500",
      hint: "Active standards in the dataset",
    },
  ];

  const confidence = data?.confidence ?? {};
  const categories = data?.categories ?? {};

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-navy-900 sm:text-2xl">
            Standards Intelligence Dashboard
          </h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink-600">
            Upload a tender or specification to identify the applicable Indian Standards, understand why
            each standard applies, and review potential specification gaps before the tender is issued.
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Link
            to="/analyze"
            className="inline-flex h-9 items-center gap-2 rounded bg-gov-600 px-4 text-sm font-medium text-white transition-colors hover:bg-gov-700"
          >
            <ScanSearch className="h-4 w-4" aria-hidden="true" />
            Analyze a tender
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded border border-crit-100 bg-crit-50 px-4 py-3 text-sm text-crit-700">
          {error} - check that the SISAP backend is running.
        </div>
      )}

      {/* Stat cards */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => <SkeletonCard key={index} />)
          : cards.map((card) => (
              <Card key={card.label}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-semibold tracking-wide text-ink-500 uppercase">
                        {card.label}
                      </p>
                      <p className="mt-2 font-mono text-2xl font-bold text-navy-900 tabular-nums">
                        {card.value.toLocaleString("en-IN")}
                      </p>
                      <p className="mt-1 text-[11px] text-ink-400">{card.hint}</p>
                    </div>
                    <card.icon className={`h-5 w-5 shrink-0 ${card.tone}`} aria-hidden="true" />
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Recent analyses */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Recent analyses</CardTitle>
              <CardDescription>Documents processed in this session</CardDescription>
            </div>
            <Link to="/history" className="text-xs font-semibold text-gov-700 hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            {loading ? (
              <div className="space-y-2 px-4 pb-4">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-8 w-full" />
                ))}
              </div>
            ) : (data?.recent_analyses.length ?? 0) === 0 ? (
              <EmptyState
                icon={<ScanSearch className="h-8 w-8" />}
                title="No analyses yet"
                description="Upload a tender PDF or paste a specification to run your first standards analysis."
                action={
                  <Link
                    to="/analyze"
                    className="inline-flex h-9 items-center gap-2 rounded bg-gov-600 px-4 text-sm font-medium text-white hover:bg-gov-700"
                  >
                    Analyze a tender
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                }
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="sisap-table">
                  <thead>
                    <tr>
                      <th>Document</th>
                      <th>Product</th>
                      <th className="text-right">Standards</th>
                      <th className="text-right">Gaps</th>
                      <th>Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.recent_analyses.map((row) => (
                      <tr key={row.document_id}>
                        <td>
                          <Link
                            to={`/analyze/${row.document_id}/recommendations`}
                            className="font-medium text-gov-700 hover:underline"
                          >
                            {row.filename}
                          </Link>
                        </td>
                        <td className="text-ink-700">{row.product}</td>
                        <td className="text-right font-mono tabular-nums">{row.standards}</td>
                        <td className="text-right font-mono tabular-nums">{row.gaps}</td>
                        <td className="whitespace-nowrap text-ink-600">{row.date}</td>
                        <td>
                          <Badge tone={row.status === "Standards identified" ? "ok" : "warn"}>{row.status}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* System + dataset status */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System status</CardTitle>
              <CardDescription>Pipeline configuration</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5 text-xs">
              <Row label="Mode" value={health?.demo_mode ? "Demo (offline)" : "Live"} />
              <Row label="Embedding model" value={health?.embedding_model ?? "-"} />
              <Row label="Embedding backend" value={health?.embedding_backend ?? "-"} />
              <Row label="FAISS vectors" value={String(health?.faiss_vectors ?? 0)} />
              <Row label="Standards loaded" value={String(health?.standards_loaded ?? 0)} />
              <Row label="API version" value={health?.version ?? "-"} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Confidence by type</CardTitle>
              <CardDescription>Average relevance score across stored analyses</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.keys(confidence).length === 0 ? (
                <p className="text-xs text-ink-400">Run an analysis to populate this panel.</p>
              ) : (
                Object.entries(confidence)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, score]) => (
                    <Progress
                      key={type}
                      value={score}
                      label={type}
                      tone={score >= 70 ? "ok" : score >= 45 ? "gov" : "warn"}
                    />
                  ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Dataset coverage</CardTitle>
              <CardDescription>Curated demo standards by category</CardDescription>
            </CardHeader>
            <CardContent>
              {Object.keys(categories).length === 0 ? (
                <Skeleton className="h-16 w-full" />
              ) : (
                <ul className="space-y-1.5">
                  {Object.entries(categories).map(([category, count]) => (
                    <li key={category} className="flex items-center justify-between gap-3 text-xs">
                      <span className="flex items-center gap-1.5 text-ink-700">
                        <Database className="h-3 w-3 text-ink-400" aria-hidden="true" />
                        {category}
                      </span>
                      <span className="font-mono text-ink-600">{count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Workflow strip */}
      <Card>
        <CardHeader>
          <CardTitle>How SISAP works</CardTitle>
          <CardDescription>
            Upload &rarr; Understand &rarr; Recommend &rarr; Validate &rarr; Explain &rarr; Report
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {[
              { step: "Upload", detail: "PDF text extraction with scanned-document detection" },
              { step: "Understand", detail: "Product, materials, performance, safety and testing requirements" },
              { step: "Recommend", detail: "Embeddings + FAISS search with composite relevance scoring" },
              { step: "Validate", detail: "Version, amendment and supersession checks" },
              { step: "Explain", detail: "Evidence-based reasons for every recommendation" },
              { step: "Report", detail: "Exportable PDF procurement analysis report" },
            ].map((item, index) => (
              <li key={item.step} className="rounded border border-ink-200 bg-ink-50/60 px-3 py-2.5">
                <span className="font-mono text-[10px] font-bold text-gov-600">STEP {index + 1}</span>
                <p className="mt-0.5 text-[13px] font-semibold text-navy-900">{item.step}</p>
                <p className="mt-0.5 text-[11px] leading-relaxed text-ink-500">{item.detail}</p>
              </li>
            ))}
          </ol>
          <p className="mt-3 flex items-center gap-1.5 text-[11px] text-ink-500">
            <FileBarChart2 className="h-3.5 w-3.5" aria-hidden="true" />
            Recommendations are generated from a curated demo dataset and require review by the
            responsible procurement/technical authority.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-ink-100 pb-1.5 last:border-0">
      <span className="text-ink-500">{label}</span>
      <span className="text-right font-medium text-ink-800">{value}</span>
    </div>
  );
}
