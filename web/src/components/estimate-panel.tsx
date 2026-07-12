import type { EstimateResponse } from "@/lib/api/client";
import { eur, pct0, pct1 } from "@/lib/format";
import { DriversChart } from "@/components/drivers-chart";

/**
 * Estimate, range, and drivers come from one payload and render together:
 * this component is only mounted when the full payload passed validation.
 */
export function EstimatePanel({ estimate }: { estimate: EstimateResponse }) {
  const span = estimate.high - estimate.low;
  const markerPct =
    span > 0
      ? Math.min(100, Math.max(0, ((estimate.estimate - estimate.low) / span) * 100))
      : 50;

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="grid gap-10 p-6 sm:p-8 lg:grid-cols-[1.1fr_1fr]">
        <div className="space-y-7">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Estimated market value
            </p>
            <p className="font-display text-5xl font-semibold tracking-tight tabular-nums sm:text-6xl">
              {eur(estimate.estimate)}
            </p>
            <p className="text-sm text-muted-foreground">
              Derived from 2018 asking prices, not a closed sale price.
            </p>
          </div>

          <div className="space-y-3">
            <div className="relative h-3 rounded-full bg-muted">
              <div className="absolute inset-y-0 left-0 right-0 rounded-full bg-primary/15" />
              <div
                className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-card bg-primary shadow-sm"
                style={{ left: `${markerPct}%` }}
                aria-hidden
              />
            </div>
            <div className="flex items-baseline justify-between gap-4 text-sm">
              <div>
                <p className="font-semibold tabular-nums">{eur(estimate.low)}</p>
                <p className="text-xs text-muted-foreground">low</p>
              </div>
              <div className="text-right">
                <p className="font-semibold tabular-nums">{eur(estimate.high)}</p>
                <p className="text-xs text-muted-foreground">high</p>
              </div>
            </div>
            <p className="max-w-prose text-sm leading-6 text-ink-soft">
              <span className="rounded-md bg-secondary px-1.5 py-0.5 font-semibold">
                {pct1(estimate.interval_test_coverage)} measured coverage
              </span>{" "}
              This {pct0(estimate.interval_coverage)} nominal interval covered{" "}
              {pct1(estimate.interval_test_coverage)} of held-out test
              properties when measured.
            </p>
          </div>
        </div>

        <div className="space-y-3 border-t border-border pt-6 lg:border-l lg:border-t-0 lg:pl-10 lg:pt-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            What moves this estimate
          </p>
          <DriversChart drivers={estimate.top_drivers} />
        </div>
      </div>
    </section>
  );
}
