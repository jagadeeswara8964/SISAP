import * as React from "react";
import { api, ApiError } from "@/services/api";
import type { RecommendationResponse } from "@/types";

export interface UseAnalysisResult {
  result: RecommendationResponse | null;
  loading: boolean;
  stage: string;
  error: string | null;
  run: (documentId?: string, text?: string) => Promise<RecommendationResponse | null>;
  reset: () => void;
}

/** Progress messages shown while the pipeline runs (spec section 27). */
const STAGES = [
  "Uploading...",
  "Extracting document...",
  "Understanding requirements...",
  "Searching standards...",
  "Analyzing relationships...",
  "Validating versions...",
  "Detecting specification gaps...",
];

/**
 * Runs the analysis pipeline and advances the visible stage so the UI never
 * appears frozen. The backend responds with the complete result.
 */
export function useAnalysis(): UseAnalysisResult {
  const [result, setResult] = React.useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [stage, setStage] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const timers = React.useRef<number[]>([]);

  const clearTimers = React.useCallback(() => {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
  }, []);

  React.useEffect(() => clearTimers, [clearTimers]);

  const run = React.useCallback(
    async (documentId?: string, text?: string) => {
      clearTimers();
      setLoading(true);
      setError(null);
      setResult(null);

      STAGES.forEach((label, index) => {
        const timer = window.setTimeout(() => setStage(label), index * 450);
        timers.current.push(timer);
      });

      try {
        const response = await api.recommend({ document_id: documentId, text });
        setResult(response);
        setStage("");
        return response;
      } catch (err: unknown) {
        const message = err instanceof ApiError ? err.message : "Analysis failed unexpectedly.";
        setError(message);
        setStage("");
        return null;
      } finally {
        clearTimers();
        setLoading(false);
      }
    },
    [clearTimers],
  );

  const reset = React.useCallback(() => {
    clearTimers();
    setResult(null);
    setError(null);
    setStage("");
  }, [clearTimers]);

  return { result, loading, stage, error, run, reset };
}
