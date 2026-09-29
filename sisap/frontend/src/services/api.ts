/** Thin typed API client for the SISAP FastAPI backend. */

import type {
  DashboardStats,
  DemoTender,
  DocumentInfo,
  ExtractResponse,
  GapsResponse,
  GraphResponse,
  HealthInfo,
  RecommendationResponse,
  ReportResponse,
  Standard,
  StandardsPage,
  UploadResponse,
} from "@/types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status = 0, code = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(
      "Could not reach the SISAP backend. Please check that the API server is running.",
      0,
      "network_error",
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : null;

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`;
    const code =
      payload && typeof payload === "object" && "code" in payload
        ? String((payload as { code: unknown }).code)
        : "error";
    throw new ApiError(detail, response.status, code);
  }

  return payload as T;
}

export const api = {
  // -- system -------------------------------------------------------------
  health: () => request<HealthInfo>("/health"),
  dashboard: () => request<DashboardStats>("/dashboard/stats"),
  demoTender: () => request<DemoTender>("/demo/tender"),

  // -- documents ----------------------------------------------------------
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<UploadResponse>("/documents/upload", { method: "POST", body });
  },
  document: (id: string) => request<DocumentInfo>(`/documents/${id}`),
  createTextDocument: (text: string) => {
    const body = new FormData();
    body.append("text", text);
    return request<UploadResponse>("/documents/text", { method: "POST", body });
  },
  extract: (id: string, useLlm = false) =>
    request<ExtractResponse>(`/documents/${id}/extract?use_llm=${useLlm}`, { method: "POST" }),

  // -- recommendations ----------------------------------------------------
  recommend: (body: { document_id?: string; text?: string; use_llm?: boolean }) =>
    request<RecommendationResponse>("/recommendations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  recommendations: (id: string) => request<RecommendationResponse>(`/recommendations/${id}`),

  // -- standards ----------------------------------------------------------
  standards: (params: {
    query?: string;
    category?: string;
    standard_type?: string;
    status?: string;
    page?: number;
    page_size?: number;
  } = {}) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") search.set(key, String(value));
    });
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<StandardsPage>(`/standards${suffix}`);
  },
  standard: (id: string) => request<Standard>(`/standards/${encodeURIComponent(id)}`),
  standardGraph: (id: string, depth = 1) =>
    request<GraphResponse>(`/standards/${encodeURIComponent(id)}/graph?depth=${depth}`),

  // -- gaps & reports -----------------------------------------------------
  gaps: (id: string) => request<GapsResponse>(`/documents/${id}/gaps`),
  report: (id: string) => request<ReportResponse>(`/reports/${id}`, { method: "POST" }),
};

/** Resolve a report download URL returned by the API. */
export function reportDownloadUrl(downloadUrl: string): string {
  return downloadUrl;
}
