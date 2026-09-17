"""Deterministic tender knockout engine.

Pure Python, zero Django/ORM/LLM dependencies. `evaluate()` takes normalized
views of a tender-or-lot and a company (`ScreenItem` / `ScreenCompany`) so the
same rule logic runs unchanged whether the caller is screening a whole tender
or a single lot within it — callers build these views from whatever ORM
fields they have (e.g. Tender.contract_value vs Lot.value).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Sequence, Tuple

HARD_FAIL = "HARD_FAIL"
FLAG = "FLAG"
CANDIDATE = "CANDIDATE"

REASON_OUT_OF_RADIUS = "Vượt bán kính hoạt động"
REASON_OUT_OF_VALUE_RANGE = "Giá trị ngoài khoảng năng lực công ty"
REASON_GUARANTEE_OVER_CEILING = "Yêu cầu bảo lãnh vượt hạn mức"
REASON_MISSING_REFERENCES = "Thiếu kinh nghiệm tham chiếu yêu cầu"
REASON_CAPABILITY_EXCLUDED = "Năng lực bị loại trừ"
REASON_GUARANTEE_NEAR_CEILING = "Bảo lãnh sát trần"
REASON_CANDIDATE = "Đáp ứng đầy đủ điều kiện sơ bộ"

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

    return CANDIDATE, REASON_CANDIDATE


def build_snippet(
    item: ScreenItem, company: ScreenCompany, verdict: str, reason: str
) -> Tuple[str, Optional[int]]:
    """Human-readable, citable explanation for a verdict. Kept separate from
    `evaluate()` so the rule function's signature stays exactly (verdict, reason).
    """

    if reason == REASON_OUT_OF_RADIUS:
        snippet = (
            f"Khoảng cách {item.distance_km} km vượt bán kính hoạt động "
            f"{company.region_radius_km} km của công ty."
        )
    elif reason == REASON_OUT_OF_VALUE_RANGE:
        snippet = (
            f"Giá trị {item.value} nằm ngoài khoảng năng lực "
            f"{company.contract_min}–{company.contract_max}."
        )
    elif reason == REASON_GUARANTEE_OVER_CEILING:
        snippet = (
            f"Bảo lãnh yêu cầu {item.guarantee_required} vượt hạn mức "
            f"{company.guarantee_ceiling} của công ty."
        )
    elif reason == REASON_MISSING_REFERENCES:
        missing = [r for r in item.references_required if r not in company.references_held]
        snippet = f"Thiếu tham chiếu bắt buộc: {', '.join(missing)}."
    elif reason == REASON_CAPABILITY_EXCLUDED:
        excluded = [r for r in item.references_required if r in company.capabilities_excluded]
        snippet = f"Yêu cầu thuộc năng lực đã loại trừ: {', '.join(excluded)}."
    elif reason == REASON_GUARANTEE_NEAR_CEILING:
        ratio = (
            (item.guarantee_required / company.guarantee_ceiling * 100)
            if company.guarantee_ceiling
            else Decimal("0")
        )
        snippet = (
            f"Bảo lãnh yêu cầu {item.guarantee_required} đạt {ratio:.1f}% hạn mức "
            f"{company.guarantee_ceiling}."
        )
    else:
        snippet = (
            "Đạt bán kính, giá trị hợp đồng, hạn mức bảo lãnh và tham chiếu yêu cầu."
        )

    return snippet, None
