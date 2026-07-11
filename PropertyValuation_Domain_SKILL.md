---
name: property-valuation-domain
description: Domain context for the explainable AVM + valuation copilot project. Load this in any subagent working on the Madrid real-estate valuation build so every agent shares the same valuation vocabulary, data rules, and honesty constraints. Trigger whenever the work touches property valuation, comparables, AVM modeling, energy/EPC, or the Streamlit valuation dashboard.
---

# Property Valuation Domain Skill

Shared context for all subagents building the explainable Automated Valuation Model for Madrid residential property. Read this before writing code or prose for the project.

## Domain context

This project sits in real estate valuation, risk, and market intelligence: property valuation, mortgage valuation for financial institutions, market analysis, energy audits, and development monitoring. This build is a prototype in that space. It estimates residential property value, explains the estimate, and packages it the way a valuation analyst would need to review it.

Design every decision so a valuation professional would trust the output. That means explainability is not optional, ranges matter more than point estimates, and comparables must be inspectable.

## Core vocabulary (use these terms consistently)

- **AVM (Automated Valuation Model)**: a model that estimates a property's market value from its attributes and comparable sales/listings.
- **Comparables ("comps")**: similar properties near the subject, used to justify a value. Similarity combines feature distance (size, rooms, type) and geographic distance.
- **Subject property**: the property being valued.
- **Asking price vs market value**: idealista18 records asking prices, not closed sale prices. Always label predictions as estimated market value derived from asking-price data, and note the gap.
- **Confidence range**: report a value interval, not just a point. Use model uncertainty or a residual-based band.
- **EPC (Energy Performance Certificate)**: energy rating band A to G. F and G are the worst and carry regulatory and value risk under EU rules.
- **Value driver**: a feature and its signed contribution to the estimate, sourced from SHAP.
- **Valuation narrative**: the short written summary combining estimate, drivers, comps, and energy flag.

## Feature conventions

- Standard tabular features: area (m2), rooms, bathrooms, floor, property type, condition, year/age, neighborhood, latitude, longitude, and the CNN condition score.
- The CNN condition score is a model-derived feature (0 to 1 or a small band) representing property/neighborhood condition from images. It is an input to the value model, not a separate output.
- Keep feature names snake_case and documented in one schema file. Every agent references that schema; no ad hoc renaming.

## Modeling rules

- LightGBM is the mandatory baseline. No deep model ships without being reported side by side against it.
- The tabular neural network and the CNN exist to add capability the baseline lacks, not to beat it at any cost. Report honest metrics (MAE, RMSE, MAPE) on a held-out set.
- SHAP explanations attach to the production value model. Cache SHAP values so the dashboard is instant.
- Never present a single number without its range and its top drivers.

## Data and honesty constraints (hard rules)

- Primary data is idealista18, which is 2018 Madrid listings. State clearly, in code comments, the README, and any user-facing text, that this is a historical prototype and not a live market feed.
- Do not scrape idealista or any restricted portal. Its API is partner-only. If a live source is ever needed, stop and ask.
- No paid APIs or paid hosting. The whole stack stays free (Streamlit Community Cloud or Hugging Face Spaces, Colab free GPU, Gemini free tier or local Ollama for the copilot LLM).
- If clean labeled property images are hard to source for the CNN, document the fallback (transfer learning on a public housing-image set) rather than inventing data.

## Writing rules for any prose (narratives, README, docs)

- Plain, direct sentences. No em dashes. Straight quotes.
- Do not use: leverage, utilize, robust, foster, seamless, empower, enhance, facilitate, streamline, crucial, pivotal, vital, showcase, delve, realm, landscape, testament, underscore.
- Back every claim with a concrete number or feature. "Estimated 340,000 euros, with size adding 40,000 and an F energy rating subtracting 15,000" beats "a strong valuation driven by key factors."
