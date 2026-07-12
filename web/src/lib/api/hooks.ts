"use client";

import { useEffect, useState } from "react";
import {
  ApiError,
  COLD_START_HINT_MS,
  type RequestOptions,
  type Subject,
} from "./client";

export type RequestState<T> =
  | { status: "idle" }
  | { status: "pending" }
  | { status: "success"; data: T }
  | { status: "error"; error: ApiError };

/**
 * Fail-closed request hook. The only way numbers reach the screen is a
 * response that passed the Zod contract check; every other outcome is an
 * explicit error state. `coldStartAt` is set (to the request start time)
 * after COLD_START_HINT_MS, or as soon as the client starts a cold-start
 * retry, so the UI can switch to the "waking the model" treatment.
 */
export function useEndpoint<T>(
  subject: Subject | null,
  fetcher: (subject: Subject, opts?: RequestOptions) => Promise<T>,
  attempt: number
) {
  const key = subject === null ? null : `${attempt}:${JSON.stringify(subject)}`;
  const [state, setState] = useState<RequestState<T>>({ status: "idle" });
  const [coldStartAt, setColdStartAt] = useState<number | null>(null);
  const [prevKey, setPrevKey] = useState<string | null>(null);

  // Render-phase adjustment: a new subject resets to pending immediately,
  // so a stale success can never be shown for the new request.
  if (key !== prevKey) {
    setPrevKey(key);
    setColdStartAt(null);
    setState(key === null ? { status: "idle" } : { status: "pending" });
  }

  useEffect(() => {
    if (subject === null || key === null) return;
    let cancelled = false;
    const requestStart = Date.now();
    const hint = setTimeout(() => {
      if (!cancelled) setColdStartAt(requestStart);
    }, COLD_START_HINT_MS);

    fetcher(subject, {
      onColdStartRetry: () => {
        if (!cancelled) setColdStartAt(requestStart);
      },
    })
      .then((data) => {
        if (!cancelled) setState({ status: "success", data });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const error =
          err instanceof ApiError
            ? err
            : new ApiError({ kind: "network", message: String(err) });
        setState({ status: "error", error });
      })
      .finally(() => {
        clearTimeout(hint);
        if (!cancelled) setColdStartAt(null);
      });

    return () => {
      cancelled = true;
      clearTimeout(hint);
    };
  }, [key, subject, fetcher]);

  return { state, coldStart: coldStartAt !== null, coldStartAt };
}
