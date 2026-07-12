import type { Driver } from "@/lib/api/client";
import { eurSigned } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Native SHAP driver chart rendered from the structured top_drivers payload.
 * Bar lengths are proportional to |shap_eur|; the printed labels are the
 * exact signed EUR values returned by the API.
 */
export function DriversChart({ drivers }: { drivers: Driver[] }) {
  const maxAbs = Math.max(...drivers.map((d) => Math.abs(d.shap_eur)));

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {drivers.map((driver) => {
          const positive = driver.shap_eur >= 0;
          const widthPct = (Math.abs(driver.shap_eur) / maxAbs) * 100;
          return (
            <div key={driver.feature} className="space-y-1">
              <div className="flex items-baseline justify-between gap-4">
                <p className="text-sm font-medium leading-5">
                  {driver.description}
                </p>
                <p
                  className={cn(
                    "shrink-0 text-sm font-semibold tabular-nums",
                    positive ? "text-positive" : "text-negative"
                  )}
                >
                  {eurSigned(driver.shap_eur)}
                </p>
              </div>
              <div className="relative h-2.5 overflow-hidden rounded-full bg-muted">
                <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                <div
                  className={cn(
                    "absolute inset-y-0 rounded-full",
                    positive
                      ? "left-1/2 bg-positive-bar"
                      : "right-1/2 bg-negative-bar"
                  )}
                  style={{ width: `${widthPct / 2}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        Signed SHAP contributions in EUR, exactly as returned by the API. Only
        the model&apos;s top {drivers.length} features are shown, so the bars
        do not sum to the estimate.
      </p>
    </div>
  );
}
