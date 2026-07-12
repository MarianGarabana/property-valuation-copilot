import { z } from "zod";
import { schemas } from "./generated";

/**
 * Base URL for the valuation API. Set NEXT_PUBLIC_API_URL at build time
 * (Vercel project env var). Defaults to the local dev API.
 */
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8600"
).replace(/\/+$/, "");

/**
 * Hard request timeout. The deployed API is a free Hugging Face Space that
 * sleeps when idle; a cold start can take tens of seconds. 90 seconds gives
 * the Space time to wake while still failing closed instead of hanging.
 */
export const REQUEST_TIMEOUT_MS = 90_000;

/** After this long in flight, the UI switches to the cold-start treatment. */
export const COLD_START_HINT_MS = 8_000;

export type ApiFailure =
  | { kind: "network"; message: string }
  | { kind: "timeout"; message: string }
  | { kind: "http"; status: number; message: string }
  | { kind: "contract"; message: string };

export class ApiError extends Error {
  readonly failure: ApiFailure;

  constructor(failure: ApiFailure) {
    super(failure.message);
    this.name = "ApiError";
    this.failure = failure;
  }
}

async function request<T>(
  path: string,
  schema: z.ZodType<T, z.ZodTypeDef, unknown>,
  init?: RequestInit
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError({
        kind: "timeout",
        message: `The valuation API did not respond within ${
          REQUEST_TIMEOUT_MS / 1000
        } seconds.`,
      });
    }
    throw new ApiError({
      kind: "network",
      message: "The valuation API could not be reached.",
    });
  }
  clearTimeout(timer);

  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.json()) as {
        error?: { message?: string };
        detail?: unknown;
      };
      detail =
        body?.error?.message ??
        (typeof body?.detail === "string" ? body.detail : "");
    } catch {
      detail = "";
    }
    throw new ApiError({
      kind: "http",
      status: res.status,
      message: detail
        ? `The valuation API returned an error (${res.status}): ${detail}`
        : `The valuation API returned an error (${res.status}).`,
    });
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new ApiError({
      kind: "contract",
      message: "The API response was not valid JSON.",
    });
  }

  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    throw new ApiError({
      kind: "contract",
      message:
        "The API response did not match the expected contract, so nothing is shown.",
    });
  }
  return parsed.data;
}

export type EstimateResponse = z.infer<typeof schemas.EstimateResponse>;
export type ComparablesResponse = z.infer<typeof schemas.ComparablesResponse>;
export type EnergyResponse = z.infer<typeof schemas.EnergyResponse>;
export type CopilotResponse = z.infer<typeof schemas.CopilotResponse>;
export type HealthResponse = z.infer<typeof schemas.HealthResponse>;
export type Driver = z.infer<typeof schemas.Driver>;
export type Comparable = z.infer<typeof schemas.Comparable>;
export type PropertyInput = z.infer<typeof schemas.PropertyInput>;

export type Subject =
  | { kind: "asset"; assetId: string }
  | { kind: "custom"; input: PropertyInput };

function endpoint<T>(path: string, schema: z.ZodType<T, z.ZodTypeDef, unknown>) {
  return (subject: Subject): Promise<T> =>
    subject.kind === "asset"
      ? request(`${path}/${encodeURIComponent(subject.assetId)}`, schema)
      : request(path, schema, {
          method: "POST",
          body: JSON.stringify(subject.input),
        });
}

export const fetchEstimate = endpoint("/v1/estimate", schemas.EstimateResponse);
export const fetchComparables = endpoint(
  "/v1/comparables",
  schemas.ComparablesResponse
);
export const fetchEnergy = endpoint("/v1/energy", schemas.EnergyResponse);
export const fetchCopilot = endpoint("/v1/copilot", schemas.CopilotResponse);

export function fetchHealth(): Promise<HealthResponse> {
  return request("/health", schemas.HealthResponse);
}
