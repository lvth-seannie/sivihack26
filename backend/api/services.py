"""Screening orchestration: adapts ORM objects to the pure rule engine in
engine.py, persists Verdict rows, and serializes results for the API."""

from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet

from storage_client.client import file_url

from . import geo
from .engine import ScreenCompany, ScreenItem, build_context, evaluate
from .models import Company, Lot, Tender, Verdict


def _resolve_source(tender: Tender) -> tuple[str, bool]:
    """Prefer our own B2-cached copy of the notice PDF over the external
    source_url - oeffentlichevergabe.de notices get archived/delisted over
    time and 404, while a cached object is ours to keep serving. Falls back
    to the external URL (with source_is_cached=False, so the frontend can
    show a staleness caveat) when nothing was ever cached."""
    if tender.raw_document_key:
        return file_url(tender.raw_document_key), True
    return tender.source_url, False


def _to_screen_company(company: Company) -> ScreenCompany:
    return ScreenCompany(
        region_radius_km=company.region_radius_km,
        contract_min=company.contract_min,
        contract_max=company.contract_max,
        guarantee_ceiling=company.guarantee_ceiling,
        references_held=list(company.references_held),
        capabilities_excluded=list(company.capabilities_excluded),
    )


def _distance_to(company: Company, tender: Tender) -> Optional[Decimal]:
    """None means "can't verify" (missing coordinates on either side) -
    engine.evaluate() treats that as FLAG, never a silent CANDIDATE pass.
    Coordinates are backfilled once via `backfill_coordinates`, never
    geocoded here at request time."""

    if company.region_lat is None or company.region_lng is None:
        return None
    if tender.location_lat is None or tender.location_lng is None:
        return None
    km = geo.haversine_km(
        float(company.region_lat),
        float(company.region_lng),
        float(tender.location_lat),
        float(tender.location_lng),
    )
    return Decimal(str(km))


def _tender_item(tender: Tender, company: Company) -> ScreenItem:
    return ScreenItem(
        distance_km=_distance_to(company, tender),
        value=tender.contract_value,
        guarantee_required=tender.guarantee_required,
        references_required=list(tender.references_required),
        data_verified=tender.extracted_at is not None,
    )


def _lot_item(lot: Lot, tender: Tender, company: Company) -> ScreenItem:
    # Lots don't carry their own extracted_at - a lot's value/guarantee/
    # references come from the same extraction pass as its parent tender.
    return ScreenItem(
        distance_km=_distance_to(company, tender),
        value=lot.value,
        guarantee_required=lot.guarantee_required,
        references_required=list(lot.references_required),
        data_verified=tender.extracted_at is not None,
    )


@transaction.atomic
def run_screening(company: Company) -> list[Verdict]:
    """Evaluate every tender and lot against `company` and persist the
    verdicts, replacing whatever was cached for this company before."""

    screen_company = _to_screen_company(company)
    tenders: QuerySet[Tender] = Tender.objects.prefetch_related("lots").order_by(
        "-extracted_at", "-id"
    )

    Verdict.objects.filter(company=company).delete()

    verdicts: list[Verdict] = []
    for tender in tenders:
        item = _tender_item(tender, company)
        verdict, reason_code = evaluate(item, screen_company)
        context = build_context(item, screen_company, reason_code, tender.source_citations)
        verdicts.append(
            Verdict(
                company=company,
                tender=tender,
                lot=None,
                verdict=verdict,
                reason_code=reason_code,
                context=context,
            )
        )

        for lot in tender.lots.all():
            lot_item = _lot_item(lot, tender, company)
            lot_verdict, lot_reason_code = evaluate(lot_item, screen_company)
            lot_context = build_context(
                lot_item, screen_company, lot_reason_code, lot.source_citations
            )
            verdicts.append(
                Verdict(
                    company=company,
                    tender=tender,
                    lot=lot,
                    verdict=lot_verdict,
                    reason_code=lot_reason_code,
                    context=lot_context,
                )
            )

    Verdict.objects.bulk_create(verdicts)
    return verdicts


def _lot_sort_key(lot_number: str):
    return (0, int(lot_number)) if lot_number.isdigit() else (1, lot_number)


def serialize_result(company: Company) -> dict:
    """Build the API payload from whatever Verdict rows are currently cached
    for `company` - does not run any evaluation itself."""

    verdicts = (
        Verdict.objects.filter(company=company)
        .select_related("tender", "lot")
        .order_by("id")
    )

    tenders_map: dict[int, dict] = {}
    order: list[int] = []
    latest_evaluated = None

    for v in verdicts:
        if v.tender_id not in tenders_map:
            tenders_map[v.tender_id] = {"tender": v.tender, "tender_verdict": None, "lots": []}
            order.append(v.tender_id)
        if v.lot_id is None:
            tenders_map[v.tender_id]["tender_verdict"] = v
        else:
            tenders_map[v.tender_id]["lots"].append(v)
        if latest_evaluated is None or v.evaluated_at > latest_evaluated:
            latest_evaluated = v.evaluated_at

    summary = {"CANDIDATE": 0, "FLAG": 0, "HARD_FAIL": 0}
    tenders_out = []

    for tid in order:
        entry = tenders_map[tid]
        tender = entry["tender"]
        tv: Optional[Verdict] = entry["tender_verdict"]
        if tv is None:
            continue
        summary[tv.verdict] += 1

        lots_out = []
        for lv in sorted(entry["lots"], key=lambda x: _lot_sort_key(x.lot.lot_number)):
            lots_out.append(
                {
                    "id": lv.lot.id,
                    "lot_number": lv.lot.lot_number,
                    "description": lv.lot.description,
                    "value": lv.lot.value,
                    "guarantee_required": lv.lot.guarantee_required,
                    "references_required": lv.lot.references_required,
                    "verdict": lv.verdict,
                    "reason_code": lv.reason_code,
                    "context": lv.context,
                    "source_page": lv.source_page,
                    "differs_from_tender": lv.verdict != tv.verdict,
                }
            )

        source_url, source_is_cached = _resolve_source(tender)
        tenders_out.append(
            {
                "id": tender.id,
                "external_id": tender.external_id,
                "title": tender.title,
                "source_url": source_url,
                "source_is_cached": source_is_cached,
                "location": tender.location,
                "contract_value": tender.contract_value,
                "guarantee_required": tender.guarantee_required,
                "references_required": tender.references_required,
                "construction_window": tender.construction_window,
                "cpv_code": tender.cpv_code,
                "published_at": tender.published_at,
                "submission_deadline": tender.submission_deadline,
                "extracted_at": tender.extracted_at,
                "verdict": tv.verdict,
                "reason_code": tv.reason_code,
                "context": tv.context,
                "source_page": tv.source_page,
                "lots": lots_out,
            }
        )

    tenders_out.sort(key=lambda t: (t["extracted_at"] is not None, t["extracted_at"]), reverse=True)

    return {
        "company": company,
        "screened": bool(order),
        "generated_at": latest_evaluated,
        "summary": summary,
        "tenders": tenders_out,
    }
