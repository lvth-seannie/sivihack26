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
REASON_CANDIDATE_OK = "CANDIDATE_OK"

_FLAG_RATIO_LOW = Decimal("0.9")
_FLAG_RATIO_HIGH = Decimal("1")


@dataclass(frozen=True)
class ScreenItem:
    """Normalized view of a tender or a lot for rule evaluation."""

    distance_km: Optional[Decimal] = None
    value: Optional[Decimal] = None
    guarantee_required: Optional[Decimal] = None
    references_required: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScreenCompany:
    """Normalized view of a company profile for rule evaluation."""

    region_radius_km: Decimal
    contract_min: Decimal
    contract_max: Decimal
    guarantee_ceiling: Decimal
    references_held: Sequence[str]
    capabilities_excluded: Sequence[str]


def evaluate(tender_or_lot: ScreenItem, company: ScreenCompany) -> Tuple[str, str]:
    item = tender_or_lot

    if item.distance_km is not None and item.distance_km > company.region_radius_km:
        return HARD_FAIL, REASON_OUT_OF_RADIUS

    if item.value is not None and (
        item.value > company.contract_max or item.value < company.contract_min
    ):
        return HARD_FAIL, REASON_OUT_OF_VALUE_RANGE

    if (
        item.guarantee_required is not None
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

    return CANDIDATE, REASON_CANDIDATE_OK


def build_context(
    item: ScreenItem, company: ScreenCompany, reason_code: str
) -> Dict[str, Any]:
    """Language-neutral facts behind a reason_code, for the frontend to
    render into a localized, citable sentence."""

    if reason_code == REASON_OUT_OF_RADIUS:
        return {
            "distance_km": item.distance_km,
            "radius_km": company.region_radius_km,
        }
    if reason_code == REASON_OUT_OF_VALUE_RANGE:
        return {
            "value": item.value,
            "min": company.contract_min,
            "max": company.contract_max,
        }
    if reason_code == REASON_GUARANTEE_OVER_CEILING:
        return {
            "guarantee_required": item.guarantee_required,
            "ceiling": company.guarantee_ceiling,
        }
    if reason_code == REASON_MISSING_REFERENCES:
        missing = [r for r in item.references_required if r not in company.references_held]
        return {"missing": missing}
    if reason_code == REASON_CAPABILITY_EXCLUDED:
        excluded = [r for r in item.references_required if r in company.capabilities_excluded]
        return {"excluded": excluded}
    if reason_code == REASON_GUARANTEE_NEAR_CEILING:
        ratio_pct = (
            (item.guarantee_required / company.guarantee_ceiling * 100)
            if company.guarantee_ceiling
            else Decimal("0")
        )
        return {
            "guarantee_required": item.guarantee_required,
            "ceiling": company.guarantee_ceiling,
            "ratio_pct": round(ratio_pct, 1),
        }
    return {}
