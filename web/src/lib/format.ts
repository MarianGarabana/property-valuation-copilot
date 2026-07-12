/**
 * Display formatting only. Every helper renders the exact value the API
 * returned in a locale format; none of them derives a new number.
 * The integer EUR display matches the API's own driver_text rendering
 * (for example 262092.92... is shown as "EUR 262,093" in both).
 */

const nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

export const eur = (value: number) => `EUR ${nf0.format(value)}`;

export const eurSigned = (value: number) =>
  value >= 0 ? `+EUR ${nf0.format(value)}` : `-EUR ${nf0.format(Math.abs(value))}`;

export const int = (value: number) => nf0.format(value);

/** Fraction from the payload (0.9030) shown as a percentage ("90.3%"). */
export const pct1 = (fraction: number) => `${(fraction * 100).toFixed(1)}%`;

/** Fraction from the payload (0.9) shown as a whole percentage ("90%"). */
export const pct0 = (fraction: number) => `${(fraction * 100).toFixed(0)}%`;

export const km = (value: number) => `${value.toFixed(2)} km`;
