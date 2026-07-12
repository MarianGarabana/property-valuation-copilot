import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "CNN condition score: evaluated and dropped",
  description:
    "The vision model study: a leakage-controlled CNN over aerial tiles, measured redundant against the existing condition feature, and removed from the value model.",
};

const signalRows = [
  ["Tile ROC AUC", "0.5929", "0.5"],
  ["Tile balanced accuracy", "0.5544", "0.5"],
  ["Tile average precision", "0.8716", "0.8217 (class prior)"],
  ["Listing ROC AUC (4,048 val listings)", "0.5924", "0.5"],
];

const ablationRows = [
  ["MAE (EUR)", "48,580", "48,884", "+303 (+0.63%)"],
  ["RMSE (EUR)", "84,124", "84,510", "+386 (+0.46%)"],
  ["MAPE (%)", "14.41", "14.51", "+0.10 pp"],
];

export default function CnnStudyPage() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-10 px-4 py-12 sm:px-6">
      <header className="space-y-4">
        <span className="inline-block rounded-full border border-error-fg/25 bg-error-bg px-3 py-1 text-xs font-semibold text-error-fg">
          Evaluated and dropped: not part of the live valuation
        </span>
        <h1 className="font-display text-3xl font-semibold leading-tight tracking-tight sm:text-5xl">
          The CNN condition score that did not make the cut
        </h1>
        <p className="text-lg leading-8 text-ink-soft">
          A vision model was part of this project&apos;s plan: score property
          condition from imagery and feed it to the value model. It was built,
          evaluated under explicit leakage controls, and measured. The
          measurement said it added nothing over a feature the model already
          had, so it was removed. This page is the record of that decision.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          What was built
        </h2>
        <p className="leading-7">
          A frozen ResNet18 probe over aerial orthophoto tiles from PNOA (IGN
          Spain, CC-BY 4.0, fetched through the free public WMS endpoint). Each
          256x256 tile covers roughly 120 m around a listing coordinate. The
          probe predicts the listing&apos;s recorded condition label: good or
          new versus needs renovation. It never trains on price; that would
          launder the regression target through the image model.
        </p>
        <p className="leading-7">
          Leakage control: listings share tiles, so no tile that holds a
          validation or test listing was allowed into CNN training. 41,757
          pure-train tiles were eligible; 25,235 tiles with any eval listing
          were excluded, along with 2,486 train listings that sit on them. All
          scoring is out-of-fold.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          The signal was real but weak
        </h2>
        <p className="leading-7">
          On a 19,997-tile stratified subset, the probe beat chance on tiles it
          never trained on. Real signal, small margin.
        </p>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full min-w-[480px] border-collapse bg-card text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2.5 font-semibold">Metric</th>
                <th className="px-4 py-2.5 font-semibold">Measured</th>
                <th className="px-4 py-2.5 font-semibold">Know-nothing baseline</th>
              </tr>
            </thead>
            <tbody>
              {signalRows.map(([metric, value, baseline]) => (
                <tr key={metric} className="border-b border-border/60 last:border-0">
                  <td className="px-4 py-2.5">{metric}</td>
                  <td className="px-4 py-2.5 font-semibold tabular-nums">{value}</td>
                  <td className="px-4 py-2.5 tabular-nums text-muted-foreground">
                    {baseline}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          The ablation that ended it
        </h2>
        <p className="leading-7">
          The question that matters is not &quot;can a CNN see condition from the air&quot; but &quot;does its score improve the value model over the condition feature it already has&quot;. Same LightGBM configuration, same 15,107
          training listings, same 4,048 validation listings, with and without
          the score:
        </p>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full min-w-[520px] border-collapse bg-card text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2.5 font-semibold">Metric</th>
                <th className="px-4 py-2.5 font-semibold">Without score</th>
                <th className="px-4 py-2.5 font-semibold">With score</th>
                <th className="px-4 py-2.5 font-semibold">Delta</th>
              </tr>
            </thead>
            <tbody>
              {ablationRows.map(([metric, without, withScore, delta]) => (
                <tr key={metric} className="border-b border-border/60 last:border-0">
                  <td className="px-4 py-2.5">{metric}</td>
                  <td className="px-4 py-2.5 tabular-nums">{without}</td>
                  <td className="px-4 py-2.5 tabular-nums">{withScore}</td>
                  <td className="px-4 py-2.5 font-semibold tabular-nums text-negative">
                    {delta}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="leading-7">
          Every metric got slightly worse. The score is by construction a noisy
          copy of the condition feature the model already reads exactly, so the
          ceiling was redundancy, not accuracy. The feature was dropped and the
          production model never shipped with it.
        </p>
      </section>

      <section className="space-y-3 rounded-xl border border-border bg-card p-6">
        <h2 className="font-display text-xl font-semibold tracking-tight">
          Why show a negative result
        </h2>
        <p className="text-sm leading-7 text-ink-soft">
          Because an AVM that quietly keeps a useless feature is less
          trustworthy than one that measures and removes it. The pipeline
          remains in the repository as a documented capability demo:
          leakage-controlled tile assignment, polite resumable downloads,
          out-of-fold scoring, and the ablation that made the call. The
          cnn_condition_score never appears in the live valuation flow of this
          app or its API.
        </p>
        <p className="text-xs leading-5 text-muted-foreground">
          Imagery attribution: Obra derivada de PNOA CC-BY 4.0 scne.es. Aerial
          tiles are from recent flights joined to 2018 listings by coordinate;
          the dates do not match, which is one more reason this stayed a demo.
        </p>
      </section>

      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href="/valuation">Back to the valuation workspace</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/">Overview</Link>
        </Button>
      </div>
    </div>
  );
}
