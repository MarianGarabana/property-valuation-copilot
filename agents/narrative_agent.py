import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents import llm

CAVEAT = (
    "Estimates come from 2018 Madrid asking prices; "
    "this is a historical prototype, not a live market feed."
)
ENERGY_DISCLAIMER = (
    "This is an observed asking-price difference between age bands, "
    "not a measured effect of the energy rating."
)
TEMPLATE_LABEL = (
    "Template narrative (no LLM backend was reachable; "
    "the text below is assembled directly from the computed figures)."
)

BANNED_WORDS = [
    "leverage",
    "utilize",
    "robust",
    "foster",
    "seamless",
    "empower",
    "enhance",
    "facilitate",
    "streamline",
    "crucial",
    "pivotal",
    "vital",
    "showcase",
    "delve",
    "realm",
    "landscape",
    "testament",
    "underscore",
]

FORBIDDEN_CHARS = {
    "—": "em dash",
    "–": "en dash",
    "“": "curly double quote",
    "”": "curly double quote",
    "‘": "curly single quote",
    "’": "curly single quote",
}

NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9])\d+(?:,\d{3})*(?:\.\d+)?")


def format_eur(value):
    return f"{value:,.0f}"


def extract_numbers(text):
    return {match.replace(",", "") for match in NUMBER_PATTERN.findall(text)}


def validate_narrative(text, facts_text, required_substrings):
    problems = []
    for char, label in FORBIDDEN_CHARS.items():
        if char in text:
            problems.append(f"contains a {label}")
    for word in BANNED_WORDS:
        if re.search(rf"\b{word}\w*\b", text, flags=re.IGNORECASE):
            problems.append(f"contains banned word '{word}'")
    for needed in required_substrings:
        if needed not in text:
            problems.append(f"missing required text '{needed}'")
    stray = extract_numbers(text) - extract_numbers(facts_text)
    if stray:
        problems.append(f"numbers not present in the facts: {sorted(stray)}")
    return problems


def build_facts(subject, valuation, comps, energy):
    facts = []

    neighborhood = subject.get("neighborhood_name") or "an area not matched to a barrio"
    rooms = int(subject["rooms"])
    bathrooms = int(subject["bathrooms"])
    facts.append(
        f"Subject property: a {subject['property_type']} in {neighborhood}, "
        f"{float(subject['area_m2']):.0f} m2, {rooms} room{'s' if rooms != 1 else ''}, "
        f"{bathrooms} bathroom{'s' if bathrooms != 1 else ''}, "
        f"condition {subject['condition']}."
    )

    coverage_pct = f"{valuation['interval_test_coverage'] * 100:.1f}"
    facts.append(
        f"Estimated market value: {format_eur(valuation['estimate'])} euros, "
        f"in a range of {format_eur(valuation['low'])} to {format_eur(valuation['high'])} euros. "
        f"The range is a 90% nominal interval that covered {coverage_pct}% of "
        f"held-out test properties when measured."
    )

    facts.append(f"Value drivers (SHAP): {valuation['driver_text']}")

    if comps is not None:
        for i, comp in enumerate(comps["comps"], start=1):
            facts.append(
                f"Comparable {i}: listed at {format_eur(comp['price'])} euros, "
                f"{comp['why']} (listing {comp['asset_id']})."
            )
        facts.append(
            f"The {comps['n']} comparables list between {format_eur(comps['price_min'])} "
            f"and {format_eur(comps['price_max'])} euros with a median of "
            f"{format_eur(comps['price_median'])} euros; the farthest is "
            f"{comps['max_distance_km']:.2f} km from the subject."
        )
    else:
        facts.append("Comparable retrieval failed; no comparables are available for this report.")

    if energy is not None:
        if energy["band"] == "unknown":
            facts.append(
                "Energy: no EPC proxy band could be derived; the build year is missing or invalid. "
                "The band would be a proxy from building age and condition, not a certificate."
            )
        else:
            year_part = (
                f"built {energy['effective_year']}"
                if energy["effective_year"] is not None
                else "new-build condition"
            )
            facts.append(
                f"Energy: EPC band {energy['band']} proxy, derived from building age and "
                f"condition ({year_part}), not a certificate."
            )
        if energy["flag"]:
            facts.append(
                "Energy risk flag: pre-1980 stock, built before the first Spanish "
                "insulation code (NBE-CT-79)."
            )
        impact = energy.get("impact")
        if impact is not None:
            direction = "lower" if impact["gap_eur_m2"] < 0 else "higher"
            facts.append(
                f"In {impact['scope']}, pre-1980 stock lists at a median of "
                f"{format_eur(impact['median_old_eur_m2'])} euros per m2 and post-2006 stock "
                f"at {format_eur(impact['median_new_eur_m2'])} euros per m2 "
                f"({format_eur(impact['n_old'])} and {format_eur(impact['n_new'])} listings "
                f"with a known build year). Applied to this property's "
                f"{impact['subject_area_m2']} m2, post-2006 stock lists "
                f"{format_eur(abs(impact['subject_gap_eur']))} euros {direction}. "
                f"{ENERGY_DISCLAIMER}"
            )
    else:
        facts.append("Energy assessment failed; no energy band is available for this report.")

    facts.append(CAVEAT)
    return facts


def required_substrings(valuation, energy):
    required = [
        format_eur(valuation["estimate"]),
        format_eur(valuation["low"]),
        format_eur(valuation["high"]),
        f"{valuation['interval_test_coverage'] * 100:.1f}",
        CAVEAT,
    ]
    if energy is not None:
        required.append("proxy")
        if energy.get("impact") is not None:
            required.append(ENERGY_DISCLAIMER)
    return required


def build_prompt(facts, required):
    banned = ", ".join(BANNED_WORDS)
    verbatim = "\n".join(f'- "{item}"' for item in required if len(item) > 20)
    facts_block = "\n".join(f"- {fact}" for fact in facts)
    return (
        "You are a valuation analyst. Write one short valuation narrative "
        "(150 to 230 words, a single flowing text, no headings, no bullet lists) "
        "from the facts below.\n\n"
        "Hard rules:\n"
        "1. Use only the facts listed below. Every number you write must appear in "
        "the facts exactly as written there. Do not round, convert, total, or invent "
        "any figure.\n"
        "2. Plain direct sentences. No em dashes, no en dashes, straight quotes only.\n"
        f"3. Never use any of these words or their variants: {banned}.\n"
        "4. Include these sentences verbatim, exactly as written, without the quotes:\n"
        f"{verbatim}\n"
        "5. State the estimate, both ends of the range, and the measured coverage "
        "figure.\n"
        "6. Call the energy band a proxy.\n\n"
        "Facts:\n"
        f"{facts_block}\n"
    )


def template_narrative(facts):
    return TEMPLATE_LABEL + "\n" + " ".join(facts)


def write_narrative(subject, valuation, comps, energy):
    if valuation is None:
        return (
            None,
            "failed",
            ["narrative_agent: valuation output missing, no summary produced"],
            None,
        )

    facts = build_facts(subject, valuation, comps, energy)
    facts_text = "\n".join(facts)
    required = required_substrings(valuation, energy)
    notes = []

    backend = llm.detect_backend()
    if backend is not None:
        try:
            text = llm.generate(build_prompt(facts, required), backend)
            problems = validate_narrative(text, facts_text, required)
            if not problems:
                return text, f"llm:{backend}", notes, facts_text
            notes.append(
                f"narrative_agent: {backend} output rejected ({'; '.join(problems)}), "
                "template fallback used"
            )
        except Exception as exc:
            notes.append(f"narrative_agent: {backend} call failed ({exc}), template fallback used")
    else:
        notes.append("narrative_agent: no LLM backend reachable, template fallback used")

    text = template_narrative(facts)
    problems = validate_narrative(text, facts_text, required)
    if problems:
        raise RuntimeError(f"template narrative failed its own validation: {problems}")
    return text, "template", notes, facts_text
