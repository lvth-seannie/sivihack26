"""Ingest German construction tenders from TED (ted.europa.eu) - the EU-wide
portal for ABOVE-THRESHOLD contracts, complementing oeffentlichevergabe.de
(which only covers below-threshold ones). Same pattern as ingest_tenders.py:
standalone, run manually, not part of the live API.

    python manage.py fetch_ted_tenders --limit 40

API: verified against the real OpenAPI spec (https://api.ted.europa.eu/api-v3.yaml,
found via /swagger -> swagger-config -> api-v3.yaml, same discipline as the
oeffentlichevergabe.de research). Anonymous POST /v3/notices/search, expert
query syntax (`field=value AND field=value SORT BY field DESC`), confirmed
against the live endpoint:

    POST https://api.ted.europa.eu/v3/notices/search
    {"query": "classification-cpv=45* AND buyer-country=DEU AND ...",
     "fields": [...], "page": 1, "limit": 100}

Each result's own `links.pdf.<LANG>` is a direct, publicly downloadable PDF
of the notice - no separate document-fetch endpoint needed. Verified for
real: 15/15 sampled TED PDFs were genuine multi-page notice text, versus
~1/124 for oeffentlichevergabe.de's equivalent endpoint (see
pdf_cache.py's PdfRenderError) - TED does not appear to have the same
"unsupported eForms version" placeholder-page problem, at least not for
the notices sampled here. This command still checks extracted text length
before treating a download as a real success, rather than assuming it.
"""

import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional

import fitz  # PyMuPDF
import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from api.models import Tender
from storage_client.client import delete_file, file_exists, upload_file

SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.0
MIN_REAL_TEXT_CHARS = 100  # below this, treat the "PDF" as a placeholder/empty, not real content
LOOKBACK_DAYS = 270  # generous window so a modest CPV-45/DEU/cn-standard pool is easy to fill

SEARCH_QUERY = (
    "classification-cpv=45* AND buyer-country=DEU AND notice-type=cn-standard "
    "AND publication-date>={since} SORT BY publication-date DESC"
)
SEARCH_FIELDS = [
    "publication-number",
    "title-proc",
    "notice-title",
    "buyer-city",
    "classification-cpv",
    "estimated-value-proc",
    "estimated-value-cur-proc",
]


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _first_i18n_value(field: Optional[dict]) -> str:
    """Fields like buyer-city/title-proc come back as {lang: value_or_list}.
    Prefer German, else whatever's first."""
    if not field:
        return ""
    value = field.get("deu") or next(iter(field.values()), "")
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _cpv_codes(notice: dict) -> list[str]:
    return [c for c in (notice.get("classification-cpv") or []) if isinstance(c, str)]


class Command(BaseCommand):
    help = "Ingest German construction (CPV 45xxxxxx) tenders from TED, deduplicated against existing tenders."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=40, help="Max number of NEW tenders to add.")

    def handle(self, *args, **options):
        limit = options["limit"]
        session = requests.Session()

        since = (date.today() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
        existing_ids = set(Tender.objects.values_list("external_id", flat=True))

        self.stdout.write(f"Searching TED (CPV 45*, DE, open calls, since {since})...")
        candidates = self._collect_candidates(session, since, limit, existing_ids)
        total_fetched = len(candidates)
        self.stdout.write(f"Found {total_fetched} new (non-duplicate) candidate(s).\n")

        real_pdf_count = 0
        inserted_count = 0
        failed_ids: list[str] = []

        for i, notice in enumerate(candidates, start=1):
            pub_number = notice["publication-number"]
            self.stdout.write(f"[{i}/{total_fetched}] TED {pub_number} ... ", ending="")
            try:
                raw_document_key = self._fetch_and_cache_pdf(session, notice)
                real_pdf_count += 1
                self._upsert_tender(notice, raw_document_key)
                inserted_count += 1
                self.stdout.write(self.style.SUCCESS("ok"))
            except Exception as exc:  # one bad notice must not kill the batch
                self.stdout.write(self.style.ERROR(f"FAILED ({exc})"))
                failed_ids.append(pub_number)
            time.sleep(REQUEST_DELAY_SECONDS)

        rate = (real_pdf_count / total_fetched * 100) if total_fetched else 0
        self.stdout.write(
            f"\nTED notices fetched: {total_fetched}\n"
            f"Real (non-placeholder) PDFs: {real_pdf_count}/{total_fetched} ({rate:.1f}%)\n"
            f"Tenders inserted/updated with a valid raw_document_key: {inserted_count}\n"
            f"Failed: {len(failed_ids)}"
        )

        if failed_ids:
            with open("failed_downloads.log", "a") as f:
                for pub_number in failed_ids:
                    f.write(f"TED:{pub_number}\n")
            self.stdout.write(self.style.WARNING("Failed publication numbers appended to failed_downloads.log"))

    def _collect_candidates(
        self, session: requests.Session, since: str, limit: int, existing_ids: set
    ) -> list[dict]:
        candidates: list[dict] = []
        seen_in_this_run: set = set()
        page = 1
        max_pages = 20  # safety cap (20 * 100 = 2000 notices scanned) in case of a very high duplicate rate

        while len(candidates) < limit and page <= max_pages:
            resp = session.post(
                SEARCH_URL,
                json={
                    "query": SEARCH_QUERY.format(since=since),
                    "fields": SEARCH_FIELDS,
                    "page": page,
                    "limit": PAGE_SIZE,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            notices = resp.json().get("notices", [])
            if not notices:
                break

            for notice in notices:
                pub_number = notice.get("publication-number")
                if not pub_number or pub_number in existing_ids or pub_number in seen_in_this_run:
                    continue
                if not any(c.startswith("45") for c in _cpv_codes(notice)):
                    continue
                seen_in_this_run.add(pub_number)
                candidates.append(notice)
                if len(candidates) >= limit:
                    break

            page += 1
            time.sleep(REQUEST_DELAY_SECONDS)

        return candidates

    def _fetch_and_cache_pdf(self, session: requests.Session, notice: dict) -> str:
        pub_number = notice["publication-number"]
        pdf_links = (notice.get("links") or {}).get("pdf") or {}
        pdf_url = pdf_links.get("DEU") or next(iter(pdf_links.values()), None)
        if not pdf_url:
            raise ValueError("no PDF link in search response")

        resp = session.get(pdf_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        doc = fitz.open(stream=resp.content, filetype="pdf")
        try:
            text = doc[0].get_text() if len(doc) else ""
        finally:
            doc.close()
        if len(text.strip()) < MIN_REAL_TEXT_CHARS:
            raise ValueError("downloaded PDF has no real text (likely a placeholder page)")

        key = f"tenders/ted-{pub_number}.pdf"
        if file_exists(key):
            delete_file(key)
        upload_file(ContentFile(resp.content), key)
        return key

    def _upsert_tender(self, notice: dict, raw_document_key: str) -> None:
        pub_number = notice["publication-number"]
        cpv_codes = _cpv_codes(notice)
        cpv_code = next((c for c in cpv_codes if c.startswith("45")), cpv_codes[0] if cpv_codes else "")
        title = _first_i18n_value(notice.get("title-proc")) or _first_i18n_value(notice.get("notice-title"))
        location = _first_i18n_value(notice.get("buyer-city"))

        contract_value = None
        if notice.get("estimated-value-cur-proc") == "EUR":
            contract_value = _to_decimal(notice.get("estimated-value-proc"))

        html_links = (notice.get("links") or {}).get("html") or {}
        source_url = html_links.get("DEU") or next(iter(html_links.values()), "")

        Tender.objects.update_or_create(
            external_id=pub_number,
            defaults={
                "title": title[:500],
                "source_url": source_url,
                "location": location[:255],
                "contract_value": contract_value,
                "cpv_code": cpv_code,
                "raw_document_key": raw_document_key,
            },
        )
