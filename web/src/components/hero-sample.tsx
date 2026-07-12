"use client";

import { useState } from "react";
import Link from "next/link";
import { fetchEstimate, type Subject } from "@/lib/api/client";
import { useEndpoint } from "@/lib/api/hooks";
import { eur, eurSigned, pct1 } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { ColdStartNotice } from "@/components/request-states";
import { cn } from "@/lib/utils";

const SAMPLE_ASSET_ID = "A10000037964896093228";

/**
 * Live sample valuation on the landing page. Same fail-closed path as the
 * workspace: a full validated payload or an explicit error, never a cached
 * number. Also warms the free model host for the next click.
 */
export function HeroSample() {
  const [subject] = useState<Subject>({
    kind: "asset",
    assetId: SAMPLE_ASSET_ID,
  });
  const { state, coldStart, coldStartAt } = useEndpoint(
    subject,
    fetchEstimate,
    0
  );

  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Live sample valuation
        </p>
        <span className="font-mono text-[10px] text-muted-foreground">
          {SAMPLE_ASSET_ID}
        </span>
      </div>

      {state.status === "pending" && coldStart ? (
        <div className="mt-4">
          <ColdStartNotice startedAt={coldStartAt} />
        </div>
      ) : state.status === "pending" ? (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      ) : state.status === "error" ? (
        <div className="mt-4 rounded-lg bg-error-bg p-4 text-sm leading-6 text-error-fg">
          <p className="font-semibold">No sample to show.</p>
          <p>{state.error.message}</p>
          <p>
            This card fetches a real valuation from the API on every load and
            shows nothing when it cannot.
          </p>
        </div>
      ) : state.status === "success" ? (
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-xs text-muted-foreground">
              Estimated market value
            </p>
            <p className="font-display text-3xl font-semibold tabular-nums">
              {eur(state.data.estimate)}
            </p>
            <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
              range {eur(state.data.low)} to {eur(state.data.high)},{" "}
              {pct1(state.data.interval_test_coverage)} measured coverage
            </p>
          </div>
          <div className="space-y-2 border-t border-border pt-4 text-sm">
            {state.data.top_drivers.map((driver) => (
              <div
                key={driver.feature}
                className="flex items-center justify-between gap-3"
              >
                <span className="leading-5">{driver.description}</span>
                <span
                  className={cn(
                    "shrink-0 font-semibold tabular-nums",
                    driver.shap_eur >= 0 ? "text-positive" : "text-negative"
                  )}
                >
                  {eurSigned(driver.shap_eur)}
                </span>
              </div>
            ))}
          </div>
          <p className="border-t border-border pt-3 text-xs leading-5 text-muted-foreground">
            Fetched from the API just now for listing{" "}
            <span className="font-mono">{SAMPLE_ASSET_ID}</span>.{" "}
            <Link href="/valuation" className="font-medium text-primary underline-offset-2 hover:underline">
              Open it in the workspace
            </Link>{" "}
            for the map, energy profile, and narrative.
          </p>
        </div>
      ) : null}
    </div>
  );
}
