import type { CopilotResponse } from "@/lib/api/client";

export function NarrativePanel({ copilot }: { copilot: CopilotResponse }) {
  return (
    <section className="space-y-5 rounded-xl border border-border bg-card p-6 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Copilot narrative
          </p>
          <h2 className="font-display text-2xl font-semibold tracking-tight">
            Written valuation summary
          </h2>
        </div>
        <span className="rounded-full border border-border bg-secondary px-3 py-1 font-mono text-xs text-ink-soft">
          source: {copilot.narrative_source}
        </span>
      </div>

      <div className="rounded-lg border border-border bg-background p-5">
        <p className="whitespace-pre-line text-[15px] leading-7">
          {copilot.text}
        </p>
      </div>

      {copilot.errors && copilot.errors.length > 0 ? (
        <ul className="space-y-1 text-xs leading-5 text-muted-foreground">
          {copilot.errors.map((err) => (
            <li key={err}>note: {err}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
