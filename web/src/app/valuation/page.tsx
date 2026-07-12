"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CaveatBanner } from "@/components/caveat-banner";
import { EstimatePanel } from "@/components/estimate-panel";
import { CompsPanel } from "@/components/comps-panel";
import { EnergyPanel } from "@/components/energy-panel";
import { NarrativePanel } from "@/components/narrative-panel";
import { LocationPicker } from "@/components/location-picker";
import {
  ColdStartNotice,
  RequestErrorState,
  SectionSkeleton,
} from "@/components/request-states";
import {
  fetchComparables,
  fetchCopilot,
  fetchEnergy,
  fetchEstimate,
  type Subject,
} from "@/lib/api/client";
import { useEndpoint } from "@/lib/api/hooks";

const EXAMPLE_ASSET_IDS = [
  "A10000037964896093228",
  "A7729945926274974123",
  "A16306045976322828349",
];

const STATIC_CAVEAT =
  "Estimates come from 2018 Madrid asking prices; this is a historical prototype, not a live market feed.";

const PROPERTY_TYPES = ["flat", "studio", "duplex"] as const;
const CONDITIONS = ["good", "new", "needs_renovation"] as const;

type CustomForm = {
  area: string;
  rooms: string;
  bathrooms: string;
  floor: string;
  propertyType: (typeof PROPERTY_TYPES)[number];
  condition: (typeof CONDITIONS)[number];
  year: string;
  location: { latitude: number; longitude: number } | null;
};

function ValuationWorkspace() {
  // Deep link: /valuation?asset_id=... starts the lookup immediately.
  const searchParams = useSearchParams();
  const linkedAssetId = searchParams.get("asset_id");

  const [subject, setSubject] = useState<Subject | null>(
    linkedAssetId ? { kind: "asset", assetId: linkedAssetId } : null
  );
  const [attempt, setAttempt] = useState(0);

  const [assetId, setAssetId] = useState(linkedAssetId ?? EXAMPLE_ASSET_IDS[0]);
  const [form, setForm] = useState<CustomForm>({
    area: "80",
    rooms: "3",
    bathrooms: "1",
    floor: "2",
    propertyType: "flat",
    condition: "good",
    year: "1970",
    location: null,
  });
  const [formError, setFormError] = useState<string | null>(null);

  const estimate = useEndpoint(subject, fetchEstimate, attempt);
  const comparables = useEndpoint(subject, fetchComparables, attempt);
  const energy = useEndpoint(subject, fetchEnergy, attempt);
  const copilot = useEndpoint(subject, fetchCopilot, attempt);

  const anyColdStart =
    estimate.coldStart ||
    comparables.coldStart ||
    energy.coldStart ||
    copilot.coldStart;
  const caveat = useMemo(() => {
    if (estimate.state.status === "success") {
      return estimate.state.data.caveat ?? STATIC_CAVEAT;
    }
    return STATIC_CAVEAT;
  }, [estimate.state]);

  const retry = () => setAttempt((n) => n + 1);

  const submitAsset = () => {
    const trimmed = assetId.trim();
    if (!trimmed) return;
    setFormError(null);
    setSubject({ kind: "asset", assetId: trimmed });
  };

  const submitCustom = () => {
    const area = Number(form.area);
    const rooms = Number(form.rooms);
    const bathrooms = Number(form.bathrooms);
    const floor = Number(form.floor);
    const year = Number(form.year);
    if (!Number.isFinite(area) || area < 15 || area > 1000) {
      setFormError("Area must be a number between 15 and 1000 m2.");
      return;
    }
    if (!Number.isInteger(rooms) || rooms < 0 || rooms > 15) {
      setFormError("Rooms must be a whole number between 0 and 15.");
      return;
    }
    if (!Number.isInteger(bathrooms) || bathrooms < 0 || bathrooms > 10) {
      setFormError("Bathrooms must be a whole number between 0 and 10.");
      return;
    }
    if (!Number.isFinite(floor) || floor < -1 || floor > 30) {
      setFormError("Floor must be a number between -1 and 30.");
      return;
    }
    if (!Number.isInteger(year) || year < 1850 || year > 2018) {
      setFormError(
        "Construction year must be a whole number between 1850 and 2018 (the dataset year)."
      );
      return;
    }
    if (!form.location) {
      setFormError("Click the map to set the property location.");
      return;
    }
    setFormError(null);
    setSubject({
      kind: "custom",
      input: {
        asset_id: null,
        area_m2: area,
        rooms,
        bathrooms,
        floor,
        property_type: form.propertyType,
        condition: form.condition,
        construction_year: year,
        property_age: 2018 - year,
        latitude: form.location.latitude,
        longitude: form.location.longitude,
        is_duplex: form.propertyType === "duplex" ? 1 : 0,
        is_studio: form.propertyType === "studio" ? 1 : 0,
      },
    });
  };

  const field = (key: keyof CustomForm) => ({
    value: String(form[key] ?? ""),
    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value })),
  });

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Valuation workspace
          </p>
          <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            Estimate a Madrid property
          </h1>
        </div>
        <CaveatBanner text={caveat} />
      </div>

      <section className="rounded-xl border border-border bg-card p-6 sm:p-8">
        <Tabs defaultValue="asset">
          <TabsList>
            <TabsTrigger value="asset">Existing listing</TabsTrigger>
            <TabsTrigger value="custom">Describe a property</TabsTrigger>
          </TabsList>

          <TabsContent value="asset" className="mt-5 space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="asset-id">Listing id (asset_id)</Label>
                <Input
                  id="asset-id"
                  value={assetId}
                  onChange={(e) => setAssetId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && submitAsset()}
                  className="font-mono text-sm"
                  placeholder="A10000037964896093228"
                />
              </div>
              <Button onClick={submitAsset} className="sm:w-auto">
                Value this listing
              </Button>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>Try:</span>
              {EXAMPLE_ASSET_IDS.map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setAssetId(id)}
                  className="rounded-md border border-border bg-background px-2 py-1 font-mono transition-colors duration-150 hover:bg-secondary"
                >
                  {id}
                </button>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="custom" className="mt-5 space-y-5">
            <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="area">Area (m2)</Label>
                  <Input id="area" type="number" inputMode="numeric" {...field("area")} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="rooms">Rooms</Label>
                  <Input id="rooms" type="number" inputMode="numeric" {...field("rooms")} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="bathrooms">Bathrooms</Label>
                  <Input
                    id="bathrooms"
                    type="number"
                    inputMode="numeric"
                    {...field("bathrooms")}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="floor">Floor</Label>
                  <Input id="floor" type="number" inputMode="numeric" {...field("floor")} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="year">Construction year</Label>
                  <Input id="year" type="number" inputMode="numeric" {...field("year")} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="property-type">Property type</Label>
                  <select
                    id="property-type"
                    value={form.propertyType}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        propertyType: e.target
                          .value as CustomForm["propertyType"],
                      }))
                    }
                    className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {PROPERTY_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="condition">Condition</Label>
                  <select
                    id="condition"
                    value={form.condition}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        condition: e.target.value as CustomForm["condition"],
                      }))
                    }
                    className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {CONDITIONS.map((c) => (
                      <option key={c} value={c}>
                        {c.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Location</Label>
                <LocationPicker
                  value={form.location}
                  onChange={(location) => setForm((f) => ({ ...f, location }))}
                />
              </div>
            </div>
            <p className="text-xs leading-5 text-muted-foreground">
              Fields not listed here (amenities, cadastral records, exact
              distances) are treated as unknown by the model, which widens the
              honest answer rather than inventing one.
            </p>
            {formError ? (
              <p className="text-sm font-medium text-negative" role="alert">
                {formError}
              </p>
            ) : null}
            <Button onClick={submitCustom}>Estimate this property</Button>
          </TabsContent>
        </Tabs>
      </section>

      {subject === null ? (
        <section className="rounded-xl border border-dashed border-input bg-card/50 p-10 text-center">
          <p className="mx-auto max-w-md text-sm leading-6 text-muted-foreground">
            Pick an existing 2018 listing or describe a property to get an
            estimate with its confidence range, SHAP drivers, comparables,
            energy profile, and written summary.
          </p>
        </section>
      ) : (
        <div className="space-y-6">
          {anyColdStart ? <ColdStartNotice /> : null}

          {estimate.state.status === "pending" ? (
            <SectionSkeleton rows={5} />
          ) : estimate.state.status === "error" ? (
            <RequestErrorState
              title="Estimate unavailable"
              error={estimate.state.error}
              onRetry={retry}
            />
          ) : estimate.state.status === "success" ? (
            <EstimatePanel estimate={estimate.state.data} />
          ) : null}

          {comparables.state.status === "pending" ? (
            <SectionSkeleton rows={4} />
          ) : comparables.state.status === "error" ? (
            <RequestErrorState
              title="Comparables unavailable"
              error={comparables.state.error}
              onRetry={retry}
            />
          ) : comparables.state.status === "success" ? (
            <CompsPanel comparables={comparables.state.data} />
          ) : null}

          {energy.state.status === "pending" ? (
            <SectionSkeleton rows={3} />
          ) : energy.state.status === "error" ? (
            <RequestErrorState
              title="Energy profile unavailable"
              error={energy.state.error}
              onRetry={retry}
            />
          ) : energy.state.status === "success" ? (
            <EnergyPanel energy={energy.state.data} />
          ) : null}

          {copilot.state.status === "pending" ? (
            <SectionSkeleton rows={6} />
          ) : copilot.state.status === "error" ? (
            <RequestErrorState
              title="Narrative unavailable"
              error={copilot.state.error}
              onRetry={retry}
            />
          ) : copilot.state.status === "success" ? (
            <NarrativePanel copilot={copilot.state.data} />
          ) : null}
        </div>
      )}
    </div>
  );
}

export default function ValuationPage() {
  return (
    <Suspense fallback={null}>
      <ValuationWorkspace />
    </Suspense>
  );
}
