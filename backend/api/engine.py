"""Deterministic tender knockout engine.

Pure Python, zero Django/ORM/LLM dependencies. `evaluate()` takes normalized
views of a tender-or-lot and a company (`ScreenItem` / `ScreenCompany`) so the
same rule logic runs unchanged whether the caller is screening a whole tender
or a single lot within it - callers build these views from whatever ORM
fields they have (e.g. Tender.contract_value vs Lot.value).

`evaluate()` returns a stable `reason_code` (not a human sentence) plus
`build_context()` returns the language-neutral facts behind it (numbers,
lists). Rendering those into an actual sentence - in whatever language the
viewer reads - is a presentation concern, done by the frontend's i18n layer.
Domain vocabulary (reference/capability labels, city names) is left exactly
as it appears in the source tender documents (German) and is never
translated - only the surrounding explanation is.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence, Tuple

HARD_FAIL = "HARD_FAIL"
FLAG = "FLAG"
CANDIDATE = "CANDIDATE"

REASON_OUT_OF_RADIUS = "OUT_OF_RADIUS"
REASON_OUT_OF_VALUE_RANGE = "OUT_OF_VALUE_RANGE"
REASON_GUARANTEE_OVER_CEILING = "GUARANTEE_OVER_CEILING"
REASON_MISSING_REFERENCES = "MISSING_REFERENCES"
REASON_CAPABILITY_EXCLUDED = "CAPABILITY_EXCLUDED"
REASON_GUARANTEE_NEAR_CEILING = "GUARANTEE_NEAR_CEILING"
REASON_LOCATION_UNVERIFIED = "LOCATION_UNVERIFIED"
REASON_PENDING_EXTRACTION = "PENDING_EXTRACTION"
REASON_CANDIDATE_OK = "CANDIDATE_OK"

_FLAG_RATIO_LOW = Decimal("0.9")
_FLAG_RATIO_HIGH = Decimal("1")

# Which extracted field's citation (from Tender/Lot.source_citations) backs
# each reason, if any - radius/value come from structured notice metadata,
# not PDF extraction, so they never have a citation.
_CITATION_FIELD_BY_REASON = {
    REASON_GUARANTEE_OVER_CEILING: "guarantee_required",
    REASON_GUARANTEE_NEAR_CEILING: "guarantee_required",
    REASON_MISSING_REFERENCES: "references_required",
    REASON_CAPABILITY_EXCLUDED: "references_required",
}


@dataclass(frozen=True)
class ScreenItem:
    """Normalized view of a tender or a lot for rule evaluation.

    data_verified should be False for a tender/lot whose rule-relevant
    fields (value, guarantee_required, references_required) haven't been
    extracted from the source document yet - those fields default to
    None/[] either way, which reads identically to "genuinely no
    requirement" further down in evaluate(). Without this flag, an
    un-extracted tender would silently look "clean" and fall through to
    CANDIDATE despite nothing actually having been checked. Defaults to
    True so existing callers/tests that don't set it are unaffected.
    """

    distance_km: Optional[Decimal] = None
    value: Optional[Decimal] = None
    guarantee_required: Optional[Decimal] = None
    references_required: Sequence[str] = field(default_factory=tuple)
    data_verified: bool = True


@dataclass(frozen=True)
class ScreenCompany:
    """Normalized view of a company profile for rule evaluation.

    guarantee_ceiling is optional: a company whose real constraint is bid
    *capacity* rather than bonding capital (see Company.weekly_bid_capacity)
    may simply not have a known ceiling - rules 3/6 are skipped, not
    hard-failed, when it's unset.
    """

    region_radius_km: Decimal
    contract_min: Decimal
    contract_max: Decimal
    guarantee_ceiling: Optional[Decimal]
    references_held: Sequence[str]
    capabilities_excluded: Sequence[str]


def evaluate(tender_or_lot: ScreenItem, company: ScreenCompany) -> Tuple[str, str]:
    """Rule order matters: a knockout that's independently verifiable from
    other data (value, guarantee, references) still fires even when
    location can't be verified - only the final "must be within radius"
    check silently passing on missing data would be the dangerous case
    (see REASON_LOCATION_UNVERIFIED below), and it doesn't, because it's
    never reached until every other hard-fail has had its say.
    """
    item = tender_or_lot

    if item.distance_km is not None and item.distance_km > company.region_radius_km:
        return HARD_FAIL, REASON_OUT_OF_RADIUS

    if item.value is not None and (
        item.value > company.contract_max or item.value < company.contract_min
    ):
        return HARD_FAIL, REASON_OUT_OF_VALUE_RANGE

    if (
        item.guarantee_required is not None
        and company.guarantee_ceiling is not None
        and item.guarantee_required > company.guarantee_ceiling
    ):
        return HARD_FAIL, REASON_GUARANTEE_OVER_CEILING

    if any(ref not in company.references_held for ref in item.references_required):
        return HARD_FAIL, REASON_MISSING_REFERENCES

    if any(ref in company.capabilities_excluded for ref in item.references_required):
        return HARD_FAIL, REASON_CAPABILITY_EXCLUDED

    if item.guarantee_required is not None and company.guarantee_ceiling:
        ratio = item.guarantee_required / company.guarantee_ceiling
        if _FLAG_RATIO_LOW <= ratio <= _FLAG_RATIO_HIGH:
            return FLAG, REASON_GUARANTEE_NEAR_CEILING

    # Nothing else disqualified it, but if we couldn't verify distance
    # (missing coordinates on the company or the tender side - e.g. not
    # backfilled yet, or the location string didn't geocode), that is NOT
    # the same as "within radius". Flag for manual review rather than
    # silently defaulting to CANDIDATE on an unverified hard constraint.
    if item.distance_km is None:
        return FLAG, REASON_LOCATION_UNVERIFIED

    # Same principle, same reason: value/guarantee/references default to
    # None/[] both when a document genuinely states no such requirement
    # AND when it simply hasn't been read yet. Without extraction having
    # run, rules 2-5 above can't tell those apart and silently pass either
    # way - so an un-extracted tender must not exit here as a confident
    # CANDIDATE either.
    if not item.data_verified:
        return FLAG, REASON_PENDING_EXTRACTION

    return CANDIDATE, REASON_CANDIDATE_OK


def build_context(
    item: ScreenItem,
    company: ScreenCompany,
    reason_code: str,
    citations: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Language-neutral facts behind a reason_code, for the frontend to
    render into a localized, citable sentence.

    `citations` is the raw Tender/Lot.source_citations dict (field name ->
    {"snippet": str, "page": int}), as captured by the extraction step. If
    the field backing this reason has a citation, it's included under the
    "citation" key so the frontend can append "(see p.14: '...')" - falling
    back to the plain reason when extraction hasn't run yet or the source
    document didn't have anything to cite.
    """

    field_name = _CITATION_FIELD_BY_REASON.get(reason_code)
    citation = (citations or {}).get(field_name) if field_name else None

    if reason_code == REASON_OUT_OF_RADIUS:
        context = {
            "distance_km": item.distance_km,
            "radius_km": company.region_radius_km,
        }
    elif reason_code == REASON_OUT_OF_VALUE_RANGE:
        context = {
            "value": item.value,
            "min": company.contract_min,
            "max": company.contract_max,
        }
    elif reason_code == REASON_GUARANTEE_OVER_CEILING:
        context = {
            "guarantee_required": item.guarantee_required,
            "ceiling": company.guarantee_ceiling,
        }
    elif reason_code == REASON_MISSING_REFERENCES:
        missing = [r for r in item.references_required if r not in company.references_held]
        context = {"missing": missing}
    elif reason_code == REASON_CAPABILITY_EXCLUDED:
        excluded = [r for r in item.references_required if r in company.capabilities_excluded]
        context = {"excluded": excluded}
    elif reason_code == REASON_GUARANTEE_NEAR_CEILING:
        ratio_pct = (
            (item.guarantee_required / company.guarantee_ceiling * 100)
            if company.guarantee_ceiling
            else Decimal("0")
        )
        context = {
            "guarantee_required": item.guarantee_required,
            "ceiling": company.guarantee_ceiling,
            "ratio_pct": round(ratio_pct, 1),
        }
    elif reason_code == REASON_LOCATION_UNVERIFIED:
        context = {"radius_km": company.region_radius_km}
    else:
        context = {}

    if citation:
        context["citation"] = citation
    return context
