"use client";

import { useEffect, useState } from "react";
import { z } from "zod";
import { ApiError, fetchHealth } from "@/lib/api/client";
import { eur, pct1 } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The API's /health payload types its model block as a loose dict, so the
 * numbers shown here are re-validated with this narrow schema. If they are
 * missing or the API is down, the strip shows an error and zero numbers.
 */
const modelBlock = z.object({
  interval_test_coverage: z.number(),
  split_id: z.string().optional(),
  test_metrics: z.object({
    mae: z.number(),
    rmse: z.number(),
    mape: z.number(),
  }),
});

type Metrics = z.infer<typeof modelBlock>;

type State =
  | { status: "pending" }
  | { status: "error"; message: string }
  | { status: "success"; metrics: Metrics };

export function HealthMetrics() {
  const [state, setState] = useState<State>({ status: "pending" });

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((health) => {
        if (cancelled) return;
        const parsed = modelBlock.safeParse(health.model);
        if (!parsed.success) {
          setState({
            status: "error",
            message:
              "The API health payload did not include the measured metrics, so none are shown.",
          });
          return;
        }
        setState({ status: "success", metrics: parsed.data });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setState({
          status: "error",
          message:
            err instanceof ApiError
              ? err.message
              : "The valuation API could not be reached.",
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "pending") {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="rounded-lg border border-error-fg/25 bg-error-bg p-5 text-sm leading-6 text-error-fg">
        {state.message} This page never substitutes cached or hardcoded
        metrics.
      </div>
    );
  }

  const { metrics } = state;
  const cards = [
    {
      label: "Mean absolute error",
      value: eur(metrics.test_metrics.mae),
    },
    {
      label: "Root mean squared error",
      value: eur(metrics.test_metrics.rmse),
    },
    {
      label: "Mean absolute % error",
      value: `${metrics.test_metrics.mape.toFixed(1)}%`,
    },
    {
      label: "Measured interval coverage",
      value: pct1(metrics.interval_test_coverage),
    },
  ];

  return (
    <div className="space-y-3">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-border bg-card p-5"
          >
            <p className="font-display text-2xl font-semibold tabular-nums">
              {card.value}
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {card.label}
            </p>
          </div>
        ))}
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        Fetched live from the valuation API health endpoint; measured once on
        the fixed held-out test split
        {metrics.split_id ? (
          <>
            {" "}
            (<span className="font-mono">{metrics.split_id}</span>)
          </>
        ) : null}
        .
      </p>
    </div>
  );
}
