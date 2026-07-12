import type { EnergyResponse } from "@/lib/api/client";
import { eur, int } from "@/lib/format";
import { cn } from "@/lib/utils";

const BAND_TONES: Record<string, string> = {
  A: "bg-positive-bg text-positive",
  B: "bg-positive-bg text-positive",
  C: "bg-positive-bg text-positive",
  D: "bg-caveat-bg text-caveat-fg",
  E: "bg-caveat-bg text-caveat-fg",
  F: "bg-error-bg text-error-fg",
  G: "bg-error-bg text-error-fg",
};

export function EnergyPanel({ energy }: { energy: EnergyResponse }) {
  const impact =
    energy.impact && !Array.isArray(energy.impact) ? energy.impact : null;
  const bandTone =
    BAND_TONES[energy.band.toUpperCase()] ?? "bg-secondary text-ink-soft";
  return (
    <section className="space-y-5 rounded-xl border border-border bg-card p-6 sm:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Energy and ESG
        </p>
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          Energy profile
        </h2>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "flex size-12 items-center justify-center rounded-lg font-display text-2xl font-bold",
              bandTone
            )}
          >
            {energy.band}
          </span>
          <div className="text-sm leading-5">
            <p className="font-semibold">
              EPC band {energy.band}
              {energy.band_is_proxy ? " (proxy)" : ""}
            </p>
            <p className="text-muted-foreground">
              {energy.band_is_proxy
                ? "Derived from building age and condition, not a certificate."
                : "From the recorded certificate."}
              {typeof energy.effective_year === "number"
                ? ` Effective year ${energy.effective_year}${
                    energy.year_source ? ` (${energy.year_source})` : ""
                  }.`
                : ""}
            </p>
          </div>
        </div>
        {energy.flag ? (
          <span className="rounded-full border border-error-fg/25 bg-error-bg px-3 py-1 text-xs font-semibold text-error-fg">
            Energy risk flag: pre-1980 stock
          </span>
        ) : (
          <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-semibold text-ink-soft">
            No energy risk flag
          </span>
        )}
      </div>

      {impact ? (
        <div className="space-y-4 rounded-lg border border-border bg-background p-5">
          <p className="text-sm font-semibold">
            Illustrative value context ({impact.scope})
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-lg font-semibold tabular-nums">
                {eur(impact.median_old_eur_m2)} / m2
              </p>
              <p className="text-xs leading-5 text-muted-foreground">
                median asking price, pre-1980 stock ({int(impact.n_old)} listings)
              </p>
            </div>
            <div>
              <p className="text-lg font-semibold tabular-nums">
                {eur(impact.median_new_eur_m2)} / m2
              </p>
              <p className="text-xs leading-5 text-muted-foreground">
                median asking price, post-2006 stock ({int(impact.n_new)} listings)
              </p>
            </div>
            <div>
              <p className="text-lg font-semibold tabular-nums">
                {eur(impact.subject_gap_eur)}
              </p>
              <p className="text-xs leading-5 text-muted-foreground">
                age-band gap of {eur(impact.gap_eur_m2)} per m2 applied to
                this property&apos;s {impact.subject_area_m2} m2
              </p>
            </div>
          </div>
          <p className="rounded-md bg-caveat-bg px-3 py-2 text-sm font-medium leading-5 text-caveat-fg">
            {energy.energy_disclaimer}
          </p>
        </div>
      ) : (
        <p className="text-sm leading-6 text-muted-foreground">
          No age-band price context is available for this property, so no
          impact figure is shown.
        </p>
      )}
    </section>
  );
}
