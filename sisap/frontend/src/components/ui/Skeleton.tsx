import { cn } from "@/utils/cn";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("sisap-skeleton h-4 w-full", className)} />;
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton key={index} className={index === lines - 1 ? "w-2/3" : "w-full"} />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded border border-ink-200 bg-white p-4">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-3 h-7 w-16" />
      <Skeleton className="mt-3 h-3 w-full" />
    </div>
  );
}
