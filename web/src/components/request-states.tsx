"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import type { ApiError } from "@/lib/api/client";
import { REQUEST_TIMEOUT_MS } from "@/lib/api/client";

/**
 * Cold-start treatment. The deployed API runs on free hosting that sleeps
 * when idle, so the first request after a pause is slow on purpose.
 */
export function ColdStartNotice({
  startedAt,
}: {
  /** When the request went pending; the elapsed counter is measured from it. */
  startedAt?: number | null;
}) {
  const [mountedAt] = useState(() => Date.now());
  const [now, setNow] = useState(mountedAt);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const elapsed = Math.max(0, Math.round((now - (startedAt ?? mountedAt)) / 1000));
  return (
    <div className="flex items-start gap-4 rounded-lg border border-border bg-card p-5">
      <span className="relative mt-1 flex size-3 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
        <span className="relative inline-flex size-3 rounded-full bg-primary" />
      </span>
      <div className="space-y-1">
        <p className="text-sm font-semibold">
          Waking the model ({elapsed}s)
        </p>
        <p className="max-w-prose text-sm leading-6 text-muted-foreground">
          The valuation API runs on free hosting that sleeps when idle. The
          first request after a pause has to wake the server and load the
          model, which can take up to a minute. The page retries automatically
          while the server wakes and stops after {REQUEST_TIMEOUT_MS / 1000}{" "}
          seconds; no numbers appear until a full response arrives.
        </p>
      </div>
    </div>
  );
}

export function SectionSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 rounded-lg border border-border bg-card p-5">
      <Skeleton className="h-5 w-44" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

/**
 * Fail-closed terminal state: an explicit error and zero numbers.
 */
export function RequestErrorState({
  title,
  error,
  onRetry,
}: {
  title: string;
  error: ApiError;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="space-y-3 rounded-lg border border-error-fg/25 bg-error-bg p-5 text-error-fg"
    >
      <div className="flex items-center gap-2">
        <svg className="size-4 shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 8v5m0 3.5v.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
        <p className="text-sm font-semibold">{title}</p>
      </div>
      <p className="text-sm leading-6">{error.message}</p>
      <p className="text-sm leading-6">
        This page shows numbers only from a verified API response, so this
        section stays empty.
      </p>
      {onRetry ? (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="border-error-fg/40 bg-transparent text-error-fg hover:bg-error-fg/10 hover:text-error-fg"
        >
          Try again
        </Button>
      ) : null}
    </div>
  );
}
