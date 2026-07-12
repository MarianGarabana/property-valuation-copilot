import Link from "next/link";
import { Button } from "@/components/ui/button";
import { CaveatBanner } from "@/components/caveat-banner";
import { HealthMetrics } from "@/components/health-metrics";
import { HeroSample } from "@/components/hero-sample";

const STATIC_CAVEAT =
  "Estimates come from 2018 Madrid asking prices; this is a historical prototype, not a live market feed.";

const steps = [
  {
    n: "01",
    title: "Point estimate",
    body: "A LightGBM model trained on about 94,800 Madrid listings from the open idealista18 dataset predicts the asking price from 38 tabular features.",
  },
  {
    n: "02",
    title: "Honest range",
    body: "Conformalized quantile regression turns the point estimate into a per-property interval. The interval is labeled with the coverage it achieved on held-out data, not the coverage it aimed for.",
  },
  {
    n: "03",
    title: "Value drivers",
    body: "SHAP attributes the estimate to concrete features in EUR: size, neighborhood, bathrooms, lift, distance to the center. No estimate ships without them.",
  },
  {
    n: "04",
    title: "Context and narrative",
    body: "Five inspectable comparables on a map, an energy proxy flag with an illustrative age-band price gap, and a written summary assembled from the computed figures.",
  },
];

const principles = [
  {
    title: "Fail closed",
    body: "If the API errors, times out, or returns a payload that breaks the contract, the page shows an explicit error and zero numbers. Never a stale figure.",
  },
  {
    title: "Ranges over points",
    body: "Every estimate carries its low and high bound, labeled with measured coverage from the payload rather than a bare nominal percentage.",
  },
  {
    title: "One source of numbers",
    body: "The frontend never recomputes or re-rounds an API value. What the model returned is what you read, in display formatting only.",
  },
  {
    title: "Illustrative stays illustrative",
    body: "The energy figure is an observed asking-price difference between age bands, and it is labeled that way everywhere it appears.",
  },
  {
    title: "Dropped features stay dropped",
    body: "A CNN condition score was built, evaluated under leakage controls, measured redundant, and removed. The write-up is public; the score is not in the model.",
  },
  {
    title: "2018, and it says so",
    body: "The data is the open idealista18 snapshot of asking prices. Every page and every API payload repeats that caveat.",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
      <section className="grid gap-10 py-14 sm:py-20 lg:grid-cols-[1.2fr_1fr] lg:items-start">
        <div className="space-y-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
            Madrid residential AVM, explained
          </p>
          <h1 className="font-display text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
            Property valuation that shows its work.
          </h1>
          <p className="max-w-xl text-lg leading-8 text-ink-soft">
            An automated valuation model for Madrid homes. Every estimate
            arrives with a confidence range, its SHAP value drivers, five
            inspectable comparables, and an energy flag. When any of that is
            missing, the app shows nothing at all.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/valuation">Estimate a property</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/cnn-study">Read the CNN study</Link>
            </Button>
          </div>
          <CaveatBanner text={STATIC_CAVEAT} />
        </div>

        <HeroSample />
      </section>

      <section className="space-y-5 py-10">
        <div>
          <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
            Measured, not promised
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            These numbers come from the live API each time this page loads. If
            the API is asleep or unreachable, this section says so instead of
            showing cached figures.
          </p>
        </div>
        <HealthMetrics />
      </section>

      <section className="space-y-6 py-10">
        <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
          How an estimate is built
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step) => (
            <div
              key={step.n}
              className="rounded-lg border border-border bg-card p-5"
            >
              <p className="font-mono text-xs text-primary">{step.n}</p>
              <p className="mt-2 font-semibold">{step.title}</p>
              <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-6 py-10">
        <div>
          <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
            The honesty rules are the product
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            A valuation tool is only useful if a professional can trust what it
            refuses to say. These rules are enforced in the API contract and
            again in this interface.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {principles.map((p) => (
            <div
              key={p.title}
              className="rounded-lg border border-border bg-card p-5"
            >
              <p className="font-semibold">{p.title}</p>
              <p className="mt-1.5 text-sm leading-6 text-muted-foreground">
                {p.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="my-10 rounded-xl bg-footer px-6 py-10 text-footer-fg sm:px-10">
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
          <div>
            <h2 className="font-display text-2xl font-semibold tracking-tight">
              Try it on a 2018 listing
            </h2>
            <p className="mt-1 max-w-xl text-sm leading-6 text-footer-muted">
              Look up a real listing by id, or describe a property and place it
              on the map. The first request can take up to a minute while the
              free model host wakes up.
            </p>
          </div>
          <Button
            asChild
            size="lg"
            className="bg-footer-fg text-footer hover:bg-footer-fg/90"
          >
            <Link href="/valuation">Open the valuation workspace</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
