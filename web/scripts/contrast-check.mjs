// WCAG 2.1 contrast check for every text/background pair used in the UI.
// Run: node scripts/contrast-check.mjs
// Fails (exit 1) if any text pair is below 4.5:1 or any large-text/graphic pair is below 3:1.

const srgb = (hex) => {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
};
const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const luminance = (hex) => {
  const [r, g, b] = srgb(hex).map(lin);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a, b) => {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
};

export const colors = {
  paper: "#FAF9F7",
  card: "#FFFFFF",
  ink: "#1A2421",
  inkSoft: "#3F4A46",
  muted: "#54605B",
  primary: "#14594A",
  primaryFg: "#FFFFFF",
  accentAmberBg: "#FAF0DB",
  accentAmberText: "#6E5308",
  accentAmberBorder: "#D9BC77",
  positiveText: "#146C43",
  positiveBg: "#E6F1EA",
  secondaryBg: "#EEF0EC",
  negativeText: "#AD2E1D",
  positiveBar: "#1B8F63",
  negativeBar: "#D14B33",
  errorBg: "#FBEDEA",
  errorText: "#8F2011",
  footerBg: "#1A2421",
  footerFg: "#F4F3EF",
  footerMuted: "#ADB8B2",
  badgeBandBg: "#FBEDEA",
  bandText: "#8F2011",
  mapLabel: "#1A2421",
};

// [name, fg, bg, minimum]
const pairs = [
  ["body text on paper", colors.ink, colors.paper, 4.5],
  ["body text on card", colors.ink, colors.card, 4.5],
  ["soft ink on paper", colors.inkSoft, colors.paper, 4.5],
  ["muted text on paper", colors.muted, colors.paper, 4.5],
  ["muted text on card", colors.muted, colors.card, 4.5],
  ["primary button text", colors.primaryFg, colors.primary, 4.5],
  ["primary link on paper", colors.primary, colors.paper, 4.5],
  ["primary link on card", colors.primary, colors.card, 4.5],
  ["caveat text on caveat bg", colors.accentAmberText, colors.accentAmberBg, 4.5],
  ["positive driver label on card", colors.positiveText, colors.card, 4.5],
  ["negative driver label on card", colors.negativeText, colors.card, 4.5],
  ["error text on error bg", colors.errorText, colors.errorBg, 4.5],
  ["positive text on positive bg", colors.positiveText, colors.positiveBg, 4.5],
  ["ink on secondary chip", colors.ink, colors.secondaryBg, 4.5],
  ["soft ink on secondary chip", colors.inkSoft, colors.secondaryBg, 4.5],
  ["caveat text on paper badge", colors.accentAmberText, colors.accentAmberBg, 4.5],
  ["footer text on footer bg", colors.footerFg, colors.footerBg, 4.5],
  ["footer muted on footer bg", colors.footerMuted, colors.footerBg, 4.5],
  ["energy band text on band bg", colors.bandText, colors.badgeBandBg, 4.5],
  // graphics / large elements: 3:1 minimum
  ["positive bar vs card", colors.positiveBar, colors.card, 3.0],
  ["negative bar vs card", colors.negativeBar, colors.card, 3.0],
  ["caveat border vs paper", colors.accentAmberBorder, colors.paper, 1.2],
];

let failed = 0;
for (const [name, fg, bg, min] of pairs) {
  const r = ratio(fg, bg);
  const ok = r >= min;
  if (!ok) failed += 1;
  console.log(
    `${ok ? "PASS" : "FAIL"}  ${r.toFixed(2)}:1  (min ${min})  ${name}  ${fg} on ${bg}`
  );
}
if (failed > 0) {
  console.error(`\n${failed} pair(s) below minimum.`);
  process.exit(1);
}
console.log("\nAll pairs pass.");
