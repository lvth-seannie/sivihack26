from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ninja import Schema


class CompanyOut(Schema):
    id: int
    name: str
    region_center: str
    region_radius_km: Decimal
    contract_min: Decimal
    contract_max: Decimal
    guarantee_ceiling: Optional[Decimal] = None
    weekly_bid_capacity: Optional[int] = None
    references_held: List[str]
    capabilities_excluded: List[str]
    available_from: Optional[date] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    revenue_eur: Optional[Decimal] = None
    description: str
    tagline: str
    can_show: List[str]
    cannot_show: List[str]


class LotResultOut(Schema):
    id: int
    lot_number: str
    description: str
    value: Optional[Decimal] = None
    guarantee_required: Optional[Decimal] = None
    references_required: List[str]
    verdict: str
    reason_code: str
    context: Dict[str, Any]
    source_page: Optional[int] = None
    differs_from_tender: bool


class TenderResultOut(Schema):
    id: int
    external_id: str
    title: str
    source_url: str
    source_is_cached: bool
    location: str
    contract_value: Optional[Decimal] = None
    guarantee_required: Optional[Decimal] = None
    references_required: List[str]
    construction_window: str
    cpv_code: str
    extracted_at: Optional[datetime] = None
    verdict: str
    reason_code: str
    context: Dict[str, Any]
    source_page: Optional[int] = None
    lots: List[LotResultOut]


class ScreenSummaryOut(Schema):
    CANDIDATE: int
    FLAG: int
    HARD_FAIL: int


class ScreenResultOut(Schema):
    company: CompanyOut
    screened: bool
    generated_at: Optional[datetime] = None
    summary: ScreenSummaryOut
    tenders: List[TenderResultOut]
