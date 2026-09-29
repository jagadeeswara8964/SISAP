import * as React from "react";
import { CheckCircle2, Info, TriangleAlert, X, XCircle } from "lucide-react";
import { cn } from "@/utils/cn";

export type ToastTone = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
}

interface ToastContextValue {
  toasts: Toast[];
  push: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

const ICONS: Record<ToastTone, React.ReactNode> = {
  success: <CheckCircle2 className="h-4 w-4 text-ok-500" aria-hidden="true" />,
  error: <XCircle className="h-4 w-4 text-crit-500" aria-hidden="true" />,
  warning: <TriangleAlert className="h-4 w-4 text-warn-500" aria-hidden="true" />,
  info: <Info className="h-4 w-4 text-gov-500" aria-hidden="true" />,
};

const BORDERS: Record<ToastTone, string> = {
  success: "border-l-ok-500",
  error: "border-l-crit-500",
  warning: "border-l-warn-500",
  info: "border-l-gov-500",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const dismiss = React.useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = React.useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((current) => [...current, { ...toast, id }].slice(-4));
      window.setTimeout(() => dismiss(id), toast.tone === "error" ? 9000 : 6000);
    },
    [dismiss],
  );

  const value = React.useMemo(() => ({ toasts, push, dismiss }), [toasts, push, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="no-print pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:items-end"
        role="region"
        aria-label="Notifications"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            aria-live="polite"
            className={cn(
              "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded border border-ink-200 border-l-4 bg-white px-4 py-3 shadow-lg",
              BORDERS[toast.tone],
            )}
          >
            <span className="mt-0.5 shrink-0">{ICONS[toast.tone]}</span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-navy-900">{toast.title}</p>
              {toast.description && (
                <p className="mt-0.5 text-xs leading-relaxed break-words text-ink-600">{toast.description}</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="shrink-0 rounded p-1 text-ink-400 transition-colors hover:bg-ink-100 hover:text-ink-700"
              aria-label="Dismiss notification"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside a ToastProvider");
  return context;
}
