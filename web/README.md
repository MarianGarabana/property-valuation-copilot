# Web frontend (Phase 6B.2)

Customer-facing Next.js app for the Property Valuation Copilot. It consumes the
FastAPI /v1 API and renders the estimate with its range and SHAP drivers, the
comparables map, the energy profile, and the copilot narrative. The data is the
2018 idealista18 snapshot; the app says so on every page.

## Run locally

1. Start the API from the repo root:
   `COPILOT_DISABLE_LLM=1 .venv/bin/python -m uvicorn api.main:app --port 8600`
2. In `web/`: `npm install`, then `npm run dev` (http://localhost:3000).

The API base URL comes from `NEXT_PUBLIC_API_URL` (see `.env.example`,
default `http://localhost:8600`). The browser calls the API directly; there is
no server proxy, so the API's `API_CORS_ORIGINS` must include the site origin.

## Scripts

- `npm run dev` / `npm run build` / `npm run start`: the usual Next.js trio.
- `npm run gen:api`: regenerates `src/lib/api/generated.ts` (Zod schemas and
  types) from the running API's OpenAPI document. Run it after any API contract
  change. Set `OPENAPI_SOURCE_URL` to point at a non-default API.
- `node scripts/contrast-check.mjs`: verifies every text/background pair in the
  palette against WCAG AA (4.5:1 text, 3:1 graphics). Exits nonzero on failure.

## Deploy (Vercel Hobby, free)

Import the `web/` directory as a Vercel project and set `NEXT_PUBLIC_API_URL`
to the Hugging Face Space URL. All pages are static; every number is fetched
client-side at view time. The free Space sleeps when idle, so the first request
can take up to a minute; the UI shows a "waking the model" state and every
request times out after 90 seconds rather than hanging.

## Honesty rules enforced here

- No client-side recomputation or re-rounding of API numbers; helpers in
  `src/lib/format.ts` do locale display formatting only.
- Fail closed: an estimate renders only from a payload that passed the Zod
  contract check, always with its range and drivers. API down, timeout, or a
  contract mismatch renders an explicit error and zero numbers.
- The interval is labeled with the measured coverage from the payload
  (`interval_test_coverage`), never a bare nominal percentage.
- The 2018-prototype caveat is in the header badge, the hero, the valuation
  page banner (verbatim from the payload once loaded), and the footer.
- The energy impact renders the payload's `energy_disclaimer` verbatim and is
  labeled illustrative.
- `cnn_condition_score` appears nowhere in the live flow; `/cnn-study` is the
  labeled "evaluated and dropped" record.
