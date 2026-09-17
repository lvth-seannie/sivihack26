"""Offline tender ingestion from oeffentlichevergabe.de.

Run manually before a demo, NOT part of the live Django API:

    python manage.py ingest_tenders --limit 50

What this does — and, importantly, what it doesn't:

- The Bekanntmachungsservice's open-data API (documented at
  /documentation/swagger-ui/opendata/) has exactly one endpoint:
  `GET /api/notice-exports?pubDay=YYYY-MM-DD` (or `pubMonth=YYYY-MM`),
  which returns a ZIP of ALL notices published that day/month. There is
  no server-side search or CPV filter - so this command downloads a
  day's export and filters client-side for CPV codes starting with "45",
  walking backwards day by day until `--limit` matches are found.

- "Attached PDF documents" in the metadata (`tender.documents[].url`)
  point at each state's own eVergabe platform (vergabe.niedersachsen.de,
  staatsanzeiger-eservices.de, etc.) - different sites, several requiring
  registration to actually download the full "Vergabeunterlagen" dossier.
  There's no uniform way to auto-download those. What IS uniformly and
  publicly downloadable for any notice is the notice's own rendered PDF,
  via `GET /api/notices/{id}?format=pdf` - that's what gets cached to B2
  here. The external dossier URL (when present) is kept as `source_url`
  so a human can click through to it.

- Rule-relevant fields the OCDS metadata almost never carries at this
  stage (guarantee_required, references_required, and contract_value
  itself in ~95% of notices) are intentionally left blank/null here.
  Filling them in is the job of the separate, not-yet-built extraction
  command that reads the cached PDF - keeping ingestion (cheap, safe to
  re-run) and extraction (slow/expensive) independent, per the brief.
"""

import io
import json
import time
import zipfile
from datetime import date, timedelta
from decimal import Decimal

import requests
from django.core.management.base import BaseCommand

from api.models import Tender
from api.pdf_cache import cache_notice_pdf

API_BASE = "https://oeffentlichevergabe.de"
EXPORTS_URL = f"{API_BASE}/api/notice-exports"
NOTICE_UI_URL = f"{API_BASE}/ui/de/notice/{{id}}"
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.5


def _cpv_codes(tender: dict) -> list[str]:
    codes = []
    for item in tender.get("items") or []:
        classification = item.get("classification") or {}
        if classification.get("scheme") == "CPV" and classification.get("id"):
            codes.append(classification["id"])
    return codes


def _location(release: dict) -> str:
    buyer = release.get("buyer") or {}
    address = buyer.get("address") or {}
    return address.get("locality") or ""


def _construction_window(tender: dict) -> str:
    period = tender.get("contractPeriod") or {}
    start, end = period.get("startDate"), period.get("endDate")
    if start and end:
        return f"{start[:10]} – {end[:10]}"
    return start[:10] if start else ""


def _source_url(tender: dict, notice_id: str) -> str:
    documents = tender.get("documents") or []
    for doc in documents:
        if doc.get("url"):
            return doc["url"]
    return NOTICE_UI_URL.format(id=notice_id)


def _iter_cpv45_tender_candidates(session: requests.Session, pub_day: date):
    """Yields (notice_id, release) for CPV-45xxxxxx tender notices published
    on `pub_day`. Returns nothing (not an error) for a quiet day/weekend."""

    resp = session.get(
        EXPORTS_URL,
        params={"pubDay": pub_day.isoformat(), "format": "ocds.zip"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        for name in archive.namelist():
            if not name.endswith(".json"):
                continue
            doc = json.loads(archive.read(name))
            for release in doc.get("releases") or []:
                if "tender" not in (release.get("tag") or []):
                    continue
                tender = release.get("tender") or {}
                notice_id = release.get("id")
                if not notice_id:
                    continue
                if any(code.startswith("45") for code in _cpv_codes(tender)):
                    yield notice_id, release


class Command(BaseCommand):
    help = "Ingest construction (CPV 45xxxxxx) tenders from oeffentlichevergabe.de into the tenders table, caching each notice's PDF to B2."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Max number of tenders to ingest.")
        parser.add_argument(
            "--days",
            type=int,
            default=5,
            help="How many days back (from yesterday) to search for candidates.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        days = options["days"]
        session = requests.Session()

        seen_ids: set[str] = set()
        candidates: list[tuple[str, dict]] = []

        day = date.today() - timedelta(days=1)
        for _ in range(days):
            if len(candidates) >= limit:
                break
            self.stdout.write(f"Scanning notice exports for {day.isoformat()} ...")
            try:
                found_today = 0
                for notice_id, release in _iter_cpv45_tender_candidates(session, day):
                    if notice_id in seen_ids:
                        continue
                    seen_ids.add(notice_id)
                    candidates.append((notice_id, release))
                    found_today += 1
                    if len(candidates) >= limit:
                        break
                self.stdout.write(f"  -> {found_today} CPV-45 tender notice(s) found")
            except requests.RequestException as exc:
                self.stdout.write(self.style.WARNING(f"  -> skipping {day.isoformat()}: {exc}"))
            day -= timedelta(days=1)
            time.sleep(REQUEST_DELAY_SECONDS)

        total = len(candidates)
        self.stdout.write(f"\nIngesting {total} tender(s)...\n")

        failed_ids: list[str] = []
        succeeded = 0

        for i, (notice_id, release) in enumerate(candidates, start=1):
            self.stdout.write(f"[{i}/{total}] tender {notice_id} ... ", ending="")
            try:
                self._ingest_one(session, notice_id, release)
                self.stdout.write(self.style.SUCCESS("ok"))
                succeeded += 1
            except Exception as exc:  # one bad tender must not kill the batch
                self.stdout.write(self.style.ERROR(f"FAILED ({exc})"))
                failed_ids.append(notice_id)
            time.sleep(REQUEST_DELAY_SECONDS)

        self.stdout.write(f"\nDone: {succeeded} succeeded, {len(failed_ids)} failed.")

        if failed_ids:
            with open("failed_tenders.log", "a") as f:
                for notice_id in failed_ids:
                    f.write(f"{notice_id}\n")
            self.stdout.write(self.style.WARNING("Failed tender IDs appended to failed_tenders.log"))

    def _ingest_one(self, session: requests.Session, notice_id: str, release: dict) -> None:
        tender = release.get("tender") or {}
        cpv_codes = _cpv_codes(tender)
        cpv_code = next((c for c in cpv_codes if c.startswith("45")), cpv_codes[0] if cpv_codes else "")
        value = tender.get("value") or {}
        amount = value.get("amount")
        contract_value = Decimal(str(amount)) if amount is not None else None

        raw_document_key = cache_notice_pdf(session, notice_id)

        Tender.objects.update_or_create(
            external_id=str(notice_id),
            defaults={
                "title": (tender.get("title") or "")[:500],
                "source_url": _source_url(tender, notice_id),
                "location": _location(release),
                "contract_value": contract_value,
                "construction_window": _construction_window(tender),
                "cpv_code": cpv_code,
                "raw_document_key": raw_document_key,
            },
        )
