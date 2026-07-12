import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";

type ComparablesResponse = {
  caveat?: string | undefined;
  asset_id?: ((string | null) | Array<string | null>) | undefined;
  method: string;
  n: number;
  comps: Array<Comparable>;
  price_min: number;
  price_max: number;
  price_median: number;
  max_distance_km: number;
  subject_latitude?: ((number | null) | Array<number | null>) | undefined;
  subject_longitude?: ((number | null) | Array<number | null>) | undefined;
};
type Comparable = {
  asset_id: string;
  price: number;
  area_m2: number;
  rooms: number;
  bathrooms: number;
  property_type: string;
  neighborhood_name?: ((string | null) | Array<string | null>) | undefined;
  distance_km: number;
  why: string;
  latitude?: ((number | null) | Array<number | null>) | undefined;
  longitude?: ((number | null) | Array<number | null>) | undefined;
};
type EnergyResponse = {
  caveat?: string | undefined;
  asset_id?: ((string | null) | Array<string | null>) | undefined;
  band: string;
  band_is_proxy: boolean;
  flag: boolean;
  effective_year?: ((number | null) | Array<number | null>) | undefined;
  year_source?: ((string | null) | Array<string | null>) | undefined;
  impact?: ((EnergyImpact | null) | Array<EnergyImpact | null>) | undefined;
  energy_disclaimer?: string | undefined;
};
type EnergyImpact = {
  scope: string;
  n_old: number;
  n_new: number;
  median_old_eur_m2: number;
  median_new_eur_m2: number;
  gap_eur_m2: number;
  subject_area_m2: number;
  subject_gap_eur: number;
};
type EstimateResponse = {
  caveat?: string | undefined;
  asset_id?: ((string | null) | Array<string | null>) | undefined;
  estimate: number;
  low: number;
  high: number;
  interval_coverage: number;
  interval_test_coverage: number;
  top_drivers: Array<Driver>;
  driver_text: string;
  shap_plot_png_base64: string;
};
type Driver = {
  feature: string;
  value?: unknown | undefined;
  shap_eur: number;
  description: string;
};
type HTTPValidationError = Partial<{
  detail: Array<ValidationError>;
}>;
type ValidationError = {
  loc: Array<(string | number) | Array<string | number>>;
  msg: string;
  type: string;
  input?: unknown | undefined;
  ctx?: {} | undefined;
};

const HealthResponse = z
  .object({ status: z.string(), model: z.object({}).partial().passthrough() })
  .passthrough();
const Driver: z.ZodType<Driver> = z
  .object({
    feature: z.string(),
    value: z.unknown().optional(),
    shap_eur: z.number(),
    description: z.string(),
  })
  .passthrough();
const EstimateResponse: z.ZodType<EstimateResponse> = z
  .object({
    caveat: z
      .string()
      .optional()
      .default(
        "Estimates come from 2018 Madrid asking prices; this is a historical prototype, not a live market feed."
      ),
    asset_id: z.union([z.string(), z.null()]).optional(),
    estimate: z.number(),
    low: z.number(),
    high: z.number(),
    interval_coverage: z.number(),
    interval_test_coverage: z.number(),
    top_drivers: z.array(Driver),
    driver_text: z.string(),
    shap_plot_png_base64: z.string(),
  })
  .passthrough();
const ValidationError: z.ZodType<ValidationError> = z
  .object({
    loc: z.array(z.union([z.string(), z.number()])),
    msg: z.string(),
    type: z.string(),
    input: z.unknown().optional(),
    ctx: z.object({}).partial().passthrough().optional(),
  })
  .passthrough();
const HTTPValidationError: z.ZodType<HTTPValidationError> = z
  .object({ detail: z.array(ValidationError) })
  .partial()
  .passthrough();
const PropertyInput = z
  .object({
    asset_id: z.union([z.string(), z.null()]),
    area_m2: z.union([z.number(), z.null()]),
    rooms: z.union([z.number(), z.null()]),
    bathrooms: z.union([z.number(), z.null()]),
    floor: z.union([z.number(), z.null()]),
    property_type: z.union([z.string(), z.null()]),
    condition: z.union([z.string(), z.null()]),
    construction_year: z.union([z.number(), z.null()]),
    cad_construction_year: z.union([z.number(), z.null()]),
    property_age: z.union([z.number(), z.null()]),
    latitude: z.union([z.number(), z.null()]),
    longitude: z.union([z.number(), z.null()]),
    neighborhood_id: z.union([z.string(), z.null()]),
    neighborhood_name: z.union([z.string(), z.null()]),
  })
  .partial()
  .passthrough();
const Comparable: z.ZodType<Comparable> = z
  .object({
    asset_id: z.string(),
    price: z.number(),
    area_m2: z.number(),
    rooms: z.number().int(),
    bathrooms: z.number().int(),
    property_type: z.string(),
    neighborhood_name: z.union([z.string(), z.null()]).optional(),
    distance_km: z.number(),
    why: z.string(),
    latitude: z.union([z.number(), z.null()]).optional(),
    longitude: z.union([z.number(), z.null()]).optional(),
  })
  .passthrough();
const ComparablesResponse: z.ZodType<ComparablesResponse> = z
  .object({
    caveat: z
      .string()
      .optional()
      .default(
        "Estimates come from 2018 Madrid asking prices; this is a historical prototype, not a live market feed."
      ),
    asset_id: z.union([z.string(), z.null()]).optional(),
    method: z.string(),
    n: z.number().int(),
    comps: z.array(Comparable),
    price_min: z.number(),
    price_max: z.number(),
    price_median: z.number(),
    max_distance_km: z.number(),
    subject_latitude: z.union([z.number(), z.null()]).optional(),
    subject_longitude: z.union([z.number(), z.null()]).optional(),
  })
  .passthrough();
const EnergyImpact: z.ZodType<EnergyImpact> = z
  .object({
    scope: z.string(),
    n_old: z.number().int(),
    n_new: z.number().int(),
    median_old_eur_m2: z.number().int(),
    median_new_eur_m2: z.number().int(),
    gap_eur_m2: z.number().int(),
    subject_area_m2: z.number().int(),
    subject_gap_eur: z.number().int(),
  })
  .passthrough();
const EnergyResponse: z.ZodType<EnergyResponse> = z
  .object({
    caveat: z
      .string()
      .optional()
      .default(
        "Estimates come from 2018 Madrid asking prices; this is a historical prototype, not a live market feed."
      ),
    asset_id: z.union([z.string(), z.null()]).optional(),
    band: z.string(),
    band_is_proxy: z.boolean(),
    flag: z.boolean(),
    effective_year: z.union([z.number(), z.null()]).optional(),
    year_source: z.union([z.string(), z.null()]).optional(),
    impact: z.union([EnergyImpact, z.null()]).optional(),
    energy_disclaimer: z
      .string()
      .optional()
      .default(
        "This is an observed asking-price difference between age bands, not a measured effect of the energy rating."
      ),
  })
  .passthrough();
const CopilotResponse = z
  .object({
    caveat: z
      .string()
      .optional()
      .default(
        "Estimates come from 2018 Madrid asking prices; this is a historical prototype, not a live market feed."
      ),
    asset_id: z.union([z.string(), z.null()]).optional(),
    text: z.string(),
    narrative_source: z.string(),
    facts: z.union([z.string(), z.null()]).optional(),
    errors: z.array(z.string()).optional(),
  })
  .passthrough();

export const schemas = {
  HealthResponse,
  Driver,
  EstimateResponse,
  ValidationError,
  HTTPValidationError,
  PropertyInput,
  Comparable,
  ComparablesResponse,
  EnergyImpact,
  EnergyResponse,
  CopilotResponse,
};

const endpoints = makeApi([
  {
    method: "get",
    path: "/health",
    alias: "health_health_get",
    requestFormat: "json",
    response: HealthResponse,
  },
  {
    method: "post",
    path: "/v1/comparables",
    alias: "comparables_posted_v1_comparables_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({
            asset_id: z.union([z.string(), z.null()]),
            area_m2: z.union([z.number(), z.null()]),
            rooms: z.union([z.number(), z.null()]),
            bathrooms: z.union([z.number(), z.null()]),
            floor: z.union([z.number(), z.null()]),
            property_type: z.union([z.string(), z.null()]),
            condition: z.union([z.string(), z.null()]),
            construction_year: z.union([z.number(), z.null()]),
            cad_construction_year: z.union([z.number(), z.null()]),
            property_age: z.union([z.number(), z.null()]),
            latitude: z.union([z.number(), z.null()]),
            longitude: z.union([z.number(), z.null()]),
            neighborhood_id: z.union([z.string(), z.null()]),
            neighborhood_name: z.union([z.string(), z.null()]),
          })
          .partial()
          .passthrough(),
      },
    ],
    response: ComparablesResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/v1/comparables/:asset_id",
    alias: "comparables_by_asset_v1_comparables__asset_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "asset_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: ComparablesResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/v1/copilot",
    alias: "copilot_posted_v1_copilot_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({
            asset_id: z.union([z.string(), z.null()]),
            area_m2: z.union([z.number(), z.null()]),
            rooms: z.union([z.number(), z.null()]),
            bathrooms: z.union([z.number(), z.null()]),
            floor: z.union([z.number(), z.null()]),
            property_type: z.union([z.string(), z.null()]),
            condition: z.union([z.string(), z.null()]),
            construction_year: z.union([z.number(), z.null()]),
            cad_construction_year: z.union([z.number(), z.null()]),
            property_age: z.union([z.number(), z.null()]),
            latitude: z.union([z.number(), z.null()]),
            longitude: z.union([z.number(), z.null()]),
            neighborhood_id: z.union([z.string(), z.null()]),
            neighborhood_name: z.union([z.string(), z.null()]),
          })
          .partial()
          .passthrough(),
      },
    ],
    response: CopilotResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/v1/copilot/:asset_id",
    alias: "copilot_by_asset_v1_copilot__asset_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "asset_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: CopilotResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/v1/energy",
    alias: "energy_posted_v1_energy_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({
            asset_id: z.union([z.string(), z.null()]),
            area_m2: z.union([z.number(), z.null()]),
            rooms: z.union([z.number(), z.null()]),
            bathrooms: z.union([z.number(), z.null()]),
            floor: z.union([z.number(), z.null()]),
            property_type: z.union([z.string(), z.null()]),
            condition: z.union([z.string(), z.null()]),
            construction_year: z.union([z.number(), z.null()]),
            cad_construction_year: z.union([z.number(), z.null()]),
            property_age: z.union([z.number(), z.null()]),
            latitude: z.union([z.number(), z.null()]),
            longitude: z.union([z.number(), z.null()]),
            neighborhood_id: z.union([z.string(), z.null()]),
            neighborhood_name: z.union([z.string(), z.null()]),
          })
          .partial()
          .passthrough(),
      },
    ],
    response: EnergyResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/v1/energy/:asset_id",
    alias: "energy_by_asset_v1_energy__asset_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "asset_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: EnergyResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/v1/estimate",
    alias: "estimate_posted_v1_estimate_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({
            asset_id: z.union([z.string(), z.null()]),
            area_m2: z.union([z.number(), z.null()]),
            rooms: z.union([z.number(), z.null()]),
            bathrooms: z.union([z.number(), z.null()]),
            floor: z.union([z.number(), z.null()]),
            property_type: z.union([z.string(), z.null()]),
            condition: z.union([z.string(), z.null()]),
            construction_year: z.union([z.number(), z.null()]),
            cad_construction_year: z.union([z.number(), z.null()]),
            property_age: z.union([z.number(), z.null()]),
            latitude: z.union([z.number(), z.null()]),
            longitude: z.union([z.number(), z.null()]),
            neighborhood_id: z.union([z.string(), z.null()]),
            neighborhood_name: z.union([z.string(), z.null()]),
          })
          .partial()
          .passthrough(),
      },
    ],
    response: EstimateResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/v1/estimate/:asset_id",
    alias: "estimate_by_asset_v1_estimate__asset_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "asset_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: EstimateResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, options);
}
