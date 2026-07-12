"use client";

import dynamic from "next/dynamic";
import type { ComparablesResponse } from "@/lib/api/client";
import { eur, km } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";

const CompsMap = dynamic(
  () => import("@/components/comps-map").then((m) => m.CompsMap),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[380px] w-full rounded-lg" />,
  }
);

export function CompsPanel({ comparables }: { comparables: ComparablesResponse }) {
  return (
    <section className="space-y-5 rounded-xl border border-border bg-card p-6 sm:p-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Comparables
          </p>
          <h2 className="font-display text-2xl font-semibold tracking-tight">
            {comparables.n} similar listings nearby
          </h2>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="rounded-md bg-secondary px-2.5 py-1 tabular-nums">
            min {eur(comparables.price_min)}
          </span>
          <span className="rounded-md bg-secondary px-2.5 py-1 tabular-nums">
            median {eur(comparables.price_median)}
          </span>
          <span className="rounded-md bg-secondary px-2.5 py-1 tabular-nums">
            max {eur(comparables.price_max)}
          </span>
          <span className="rounded-md bg-secondary px-2.5 py-1 tabular-nums">
            farthest {km(comparables.max_distance_km)}
          </span>
        </div>
      </div>

      <CompsMap comparables={comparables} />

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th className="py-2 pr-4 font-semibold">Listing</th>
              <th className="py-2 pr-4 font-semibold">Asking price</th>
              <th className="py-2 pr-4 font-semibold">Area</th>
              <th className="py-2 pr-4 font-semibold">Rooms</th>
              <th className="py-2 pr-4 font-semibold">Baths</th>
              <th className="py-2 pr-4 font-semibold">Distance</th>
              <th className="py-2 font-semibold">Neighborhood</th>
            </tr>
          </thead>
          <tbody>
            {comparables.comps.map((comp) => (
              <tr key={comp.asset_id} className="border-b border-border/60">
                <td className="py-2.5 pr-4 font-mono text-xs text-ink-soft">
                  {comp.asset_id}
                </td>
                <td className="py-2.5 pr-4 font-semibold tabular-nums">
                  {eur(comp.price)}
                </td>
                <td className="py-2.5 pr-4 tabular-nums">{comp.area_m2} m2</td>
                <td className="py-2.5 pr-4 tabular-nums">{comp.rooms}</td>
                <td className="py-2.5 pr-4 tabular-nums">{comp.bathrooms}</td>
                <td className="py-2.5 pr-4 tabular-nums">{km(comp.distance_km)}</td>
                <td className="py-2.5">{comp.neighborhood_name ?? "unknown"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs leading-5 text-muted-foreground">
        Selection method, verbatim from the API: {comparables.method}.
      </p>
    </section>
  );
}
