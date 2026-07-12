export function SiteFooter() {
  return (
    <footer className="mt-16 bg-footer text-footer-fg">
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-xl space-y-2">
            <p className="font-display text-lg font-semibold">
              Property Valuation Copilot
            </p>
            <p className="text-sm leading-6 text-footer-muted">
              A student prototype of an explainable automated valuation model
              for Madrid residential property. Estimates come from 2018 Madrid
              asking prices (idealista18); this is a historical prototype, not
              a live market feed.
            </p>
          </div>
          <div className="space-y-2 text-sm text-footer-muted">
            <p>Marian Garabana, MSc Business Analytics and Data Science</p>
            <p>IE University, Madrid</p>
            <p>Free stack: LightGBM, SHAP, FastAPI, Next.js, MapLibre</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
