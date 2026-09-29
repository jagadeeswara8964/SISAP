import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  FileText,
  FileUp,
  Info,
  ScanSearch,
  Sparkles,
  Trash2,
} from "lucide-react";
import { api, ApiError } from "@/services/api";
import { useAnalysis } from "@/hooks/useAnalysis";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { RequirementsPanel } from "@/components/RequirementsPanel";
import type { RequirementObject, UploadResponse } from "@/types";

type Mode = "upload" | "paste";

const STAGE_MESSAGES = [
  "Uploading...",
  "Extracting document...",
  "Understanding requirements...",
  "Searching standards...",
  "Analyzing relationships...",
  "Validating versions...",
  "Detecting specification gaps...",
];

export default function AnalyzePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { push } = useToast();

  const [mode, setMode] = React.useState<Mode>("upload");
  const [file, setFile] = React.useState<File | null>(null);
  const [text, setText] = React.useState("");
  const [upload, setUpload] = React.useState<UploadResponse | null>(null);
  const [requirements, setRequirements] = React.useState<RequirementObject | null>(null);
  const [method, setMethod] = React.useState("");
  const [busy, setBusy] = React.useState<string | null>(null);
  const [stageIndex, setStageIndex] = React.useState(-1);
  const [error, setError] = React.useState<string | null>(null);
  const [showReset, setShowReset] = React.useState(false);
  const [dragging, setDragging] = React.useState(false);
  const [sections, setSections] = React.useState<{ key: string; title: string; characters: number }[]>([]);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const analysis = useAnalysis();

  const documentId = upload?.document_id ?? searchParams.get("documentId") ?? null;

  // Advance the visible stage while a request is in flight.
  React.useEffect(() => {
    if (!busy) {
      setStageIndex(-1);
      return;
    }
    let index = 0;
    setStageIndex(0);
    const timer = window.setInterval(() => {
      index = Math.min(index + 1, STAGE_MESSAGES.length - 1);
      setStageIndex(index);
    }, 900);
    return () => window.clearInterval(timer);
  }, [busy]);

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!file) {
      setError("Select a tender or specification PDF to upload.");
      return;
    }

    setBusy("upload");
    try {
      const result = await api.upload(file);
      setUpload(result);

      if (result.is_scanned || result.extraction_status !== "ok") {
        setRequirements(null);
        setError(result.message || "Text could not be reliably extracted. OCR is required for this document.");
        push({
          tone: "warning",
          title: "Text extraction incomplete",
          description: result.message,
        });
        return;
      }

      push({ tone: "success", title: "Document uploaded", description: result.filename });
      const extracted = await api.extract(result.document_id);
      setRequirements(extracted.requirements);
      setMethod(extracted.extraction_method);
      setSections(extracted.sections ?? []);
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : "Upload failed unexpectedly.";
      setError(message);
      push({ tone: "error", title: "Upload failed", description: message });
    } finally {
      setBusy(null);
    }
  };

  const handlePasteSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (text.trim().length < 40) {
      setError("Paste at least a short paragraph of specification text (minimum 40 characters).");
      return;
    }

    setBusy("paste");
    try {
      const result = await api.createTextDocument(text);
      setUpload(result);
      const extracted = await api.extract(result.document_id);
      setRequirements(extracted.requirements);
      setMethod(extracted.extraction_method);
      setSections(extracted.sections ?? []);
      push({ tone: "success", title: "Specification received", description: "Requirements extracted." });
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : "Could not process the pasted specification.";
      setError(message);
      push({ tone: "error", title: "Processing failed", description: message });
    } finally {
      setBusy(null);
    }
  };

  const loadDemoTender = async () => {
    setError(null);
    setBusy("demo");
    try {
      const demo = await api.demoTender();
      setMode("paste");
      setText(demo.text);
      push({
        tone: "info",
        title: "Demo tender loaded",
        description: `${demo.filename} - review and click "Extract requirements"`,
      });
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : "Could not load the demo tender.";
      setError(message);
      push({ tone: "error", title: "Demo unavailable", description: message });
    } finally {
      setBusy(null);
    }
  };

  const findStandards = async () => {
    if (!documentId) return;
    setError(null);
    const result = await analysis.run(documentId);
    if (result) {
      push({
        tone: "success",
        title: "Standards identified",
        description: `${result.summary.total} standards, ${result.summary.potential_gaps} potential gaps.`,
      });
      navigate(`/analyze/${documentId}/recommendations`);
    } else if (analysis.error) {
      setError(analysis.error);
      push({ tone: "error", title: "Analysis failed", description: analysis.error });
    }
  };

  const reset = () => {
    setFile(null);
    setText("");
    setUpload(null);
    setRequirements(null);
    setMethod("");
    setSections([]);
    setError(null);
    setShowReset(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-navy-900">Analyze Tender</h1>
          <p className="mt-1 max-w-2xl text-sm text-ink-600">
            Upload a tender/specification PDF or paste the specification text. SISAP extracts the
            requirements, then identifies the applicable Indian Standards.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadDemoTender} loading={busy === "demo"}>
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Load demo tender
          </Button>
          {(upload || text) && (
            <Button variant="ghost" size="sm" onClick={() => setShowReset(true)}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              Clear
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2.5 rounded border border-crit-100 bg-crit-50 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-crit-500" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-crit-700">Something needs attention</p>
            <p className="mt-0.5 text-xs leading-relaxed text-crit-700">{error}</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* LEFT: input */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-0">
              <div className="flex gap-1" role="tablist" aria-label="Input method">
                {(
                  [
                    { id: "upload", label: "Upload PDF", icon: FileUp },
                    { id: "paste", label: "Paste specification", icon: FileText },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.id}
                    role="tab"
                    aria-selected={mode === tab.id}
                    onClick={() => setMode(tab.id)}
                    className={`flex items-center gap-2 rounded-t border-b-2 px-3.5 py-2.5 text-[13px] font-medium transition-colors ${
                      mode === tab.id
                        ? "border-gov-600 text-gov-700"
                        : "border-transparent text-ink-500 hover:text-ink-800"
                    }`}
                  >
                    <tab.icon className="h-4 w-4" aria-hidden="true" />
                    {tab.label}
                  </button>
                ))}
              </div>
            </CardHeader>

            <CardContent className="pt-4">
              {mode === "upload" ? (
                <form onSubmit={handleUpload} className="space-y-3.5">
                  <div
                    onDragOver={(event) => {
                      event.preventDefault();
                      setDragging(true);
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(event) => {
                      event.preventDefault();
                      setDragging(false);
                      const dropped = event.dataTransfer.files?.[0];
                      if (dropped) setFile(dropped);
                    }}
                    className={`rounded border-2 border-dashed px-4 py-8 text-center transition-colors ${
                      dragging ? "border-gov-500 bg-gov-50" : "border-ink-300 bg-ink-50/50"
                    }`}
                  >
                    <FileUp className="mx-auto h-8 w-8 text-ink-400" aria-hidden="true" />
                    <p className="mt-2 text-sm font-medium text-ink-700">
                      Drag and drop a tender PDF, or browse
                    </p>
                    <p className="mt-1 text-xs text-ink-400">PDF files up to 25 MB. Text-based PDFs only.</p>
                    <input
                      ref={inputRef}
                      id="tender-file"
                      type="file"
                      accept="application/pdf,.pdf"
                      onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                      className="mx-auto mt-3 block w-full max-w-xs text-xs text-ink-600 file:mr-3 file:rounded file:border-0 file:bg-gov-600 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-gov-700"
                      aria-label="Tender PDF file"
                    />
                    {file && (
                      <p className="mt-2 text-xs font-medium text-gov-700">
                        Selected: {file.name} ({(file.size / 1024).toFixed(0)} KB)
                      </p>
                    )}
                  </div>

                  <Button type="submit" loading={busy === "upload"} disabled={!file} className="w-full">
                    <ScanSearch className="h-4 w-4" aria-hidden="true" />
                    Upload and extract requirements
                  </Button>
                </form>
              ) : (
                <form onSubmit={handlePasteSubmit} className="space-y-3.5">
                  <div>
                    <label htmlFor="spec-text" className="mb-1.5 block text-xs font-semibold text-ink-600">
                      Product / tender specification text
                    </label>
                    <Textarea
                      id="spec-text"
                      rows={14}
                      value={text}
                      onChange={(event) => setText(event.target.value)}
                      placeholder="Paste the scope of supply, technical specification, safety, testing and installation clauses here..."
                      className="font-mono text-xs leading-relaxed"
                    />
                    <p className="mt-1.5 text-[11px] text-ink-400">
                      {text.trim().length} characters. Minimum 40 characters.
                    </p>
                  </div>
                  <Button type="submit" loading={busy === "paste"} disabled={text.trim().length < 40} className="w-full">
                    <ScanSearch className="h-4 w-4" aria-hidden="true" />
                    Extract requirements
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>

          {/* Document preview */}
          {upload && (
            <Card>
              <CardHeader>
                <CardTitle>Document</CardTitle>
                <CardDescription>Extraction summary</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5 text-xs">
                <MetaRow label="File" value={upload.filename} />
                <MetaRow label="Document ID" value={upload.document_id} mono />
                <MetaRow label="Pages" value={String(upload.page_count || "-")} />
                <MetaRow label="Characters extracted" value={upload.char_count.toLocaleString("en-IN")} />
                <div className="flex items-center justify-between gap-3 border-t border-ink-100 pt-2.5">
                  <span className="text-ink-500">Extraction status</span>
                  <Badge tone={upload.extraction_status === "ok" ? "ok" : "warn"}>
                    {upload.extraction_status === "ok" ? "Text extracted" : upload.extraction_status}
                  </Badge>
                </div>
                {sections.length > 0 && (
                  <div className="border-t border-ink-100 pt-2.5">
                    <p className="text-ink-500">Sections detected</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {sections.slice(0, 10).map((section) => (
                        <Badge key={section.key} tone="neutral" title={`${section.characters} characters`}>
                          {section.title}
                        </Badge>
                      ))}
                      {sections.length > 10 && (
                        <Badge tone="neutral">+{sections.length - 10} more</Badge>
                      )}
                    </div>
                  </div>
                )}

                {upload.is_scanned && (
                  <div className="flex items-start gap-2 rounded border border-warn-100 bg-warn-50 px-3 py-2">
                    <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn-500" aria-hidden="true" />
                    <p className="text-[11px] leading-relaxed text-warn-700">
                      Text could not be reliably extracted. OCR is required for this document. OCR is not
                      enabled in this deployment.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* RIGHT: extracted requirements */}
        <div className="space-y-4">
          <RequirementsPanel requirements={requirements} method={method} loading={Boolean(busy)} />

          <Card className={requirements ? "border-gov-200 bg-gov-50/50" : ""}>
            <CardContent className="pt-4">
              <Button
                onClick={findStandards}
                loading={analysis.loading}
                disabled={!documentId || !requirements}
                size="lg"
                className="w-full"
              >
                <ScanSearch className="h-4 w-4" aria-hidden="true" />
                Find Applicable Standards
              </Button>
              <p className="mt-2 text-center text-[11px] leading-relaxed text-ink-500">
                Runs semantic search over the standards database, expands the relationship graph,
                validates versions and detects specification gaps.
              </p>
            </CardContent>
          </Card>

          {(busy || analysis.loading) && (
            <Card>
              <CardContent className="flex items-center gap-3 pt-4">
                <Spinner className="text-gov-600" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-navy-900">
                    {analysis.loading
                      ? analysis.stage || "Working..."
                      : STAGE_MESSAGES[Math.max(stageIndex, 0)]}
                  </p>
                  <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-ink-200">
                    <div
                      className="h-full rounded-full bg-gov-600 transition-all duration-700"
                      style={{
                        width: `${
                          ((Math.max(stageIndex, 0) + 1) / STAGE_MESSAGES.length) * 100
                        }%`,
                      }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={showReset}
        title="Clear the current analysis?"
        message="The uploaded document, extracted requirements and any results in this session will be discarded from the form. Stored history is not affected."
        confirmLabel="Clear"
        tone="danger"
        onConfirm={reset}
        onCancel={() => setShowReset(false)}
      />
    </div>
  );
}

function MetaRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-ink-500">{label}</span>
      <span className={`text-right font-medium text-ink-800 ${mono ? "font-mono text-[11px]" : ""}`}>{value}</span>
    </div>
  );
}
