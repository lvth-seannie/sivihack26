"""One-time backfill: fill published_at/submission_deadline on Tender rows
that were ingested before those fields existed on the model.

    python manage.py backfill_tender_dates

Safe to re-run - only rows still missing both dates are touched, split by
which pipeline originally ingested them (source_url is the only reliable
signal we have after the fact, since none of the ingest commands recorded
their own source name):

- oeffentlichevergabe.de (source_url .../ui/de/notice/{id}): re-fetches
  each notice's raw XML (pdf_cache.fetch_notice_dates) - the bulk OCDS
  export used by ingest_tenders.py never carries either date at all
  (confirmed by scanning a full day's export: 0/666 "tender"-tagged
  releases had a tenderPeriod), only the per-notice XML does.
- TED (source_url ted.europa.eu/...): one batched search call with all
  missing publication-numbers OR'd together - both dates are ordinary
  fields on the same search endpoint fetch_ted_tenders.py already uses,
  just weren't in its requested field list before.
- Everything else: tries notice_clean.csv (the teammate's clean_data CSV
  import, already on disk) for publicationDate by external_id match. In
  practice this currently matches nothing, because the only other source
  in the DB is seed_data.py's hand-authored demo fixtures (evergabe-online.de
  URLs, external_ids like "TND-2026-0101") - not real ingested notices, so
  there is no raw date to recover for them and both fields stay null. Kept
  as a fallback in case load_cleaned_tenders.py-sourced rows exist too.
  Either way, submission_deadline is never set here - the raw_data tables
  behind notice_clean.csv never captured it at all (confirmed by
  inspecting every raw_data/*.csv header), so it's left null, not
  fabricated.
"""

import time
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from api.management.commands.fetch_ted_tenders import _earliest_date, _to_date as _ted_to_date
from api.models import Tender
from api.pdf_cache import fetch_notice_dates

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
TED_BATCH_SIZE = 40
REQUEST_TIMEOUT = 30
OE_REQUEST_DELAY_SECONDS = 1.2
CLEANED_DIR = Path(settings.BASE_DIR) / "database" / "clean_data"


class Command(BaseCommand):
    help = "Backfill published_at/submission_deadline on Tender rows ingested before those fields existed."

    def handle(self, *args, **options):
        missing = Q(published_at__isnull=True) | Q(submission_deadline__isnull=True)

        oe_qs = Tender.objects.filter(missing, source_url__icontains="oeffentlichevergabe.de/ui/de/notice")
        ted_qs = Tender.objects.filter(missing, source_url__icontains="ted.europa.eu")
        other_qs = Tender.objects.filter(missing).exclude(
            source_url__icontains="oeffentlichevergabe.de/ui/de/notice"
        ).exclude(source_url__icontains="ted.europa.eu")

        self._backfill_oeffentlichevergabe(oe_qs)
        self._backfill_ted(ted_qs)
        self._backfill_from_cleaned_csv(other_qs)

    def _backfill_oeffentlichevergabe(self, qs) -> None:
        total = qs.count()
        self.stdout.write(f"oeffentlichevergabe.de: {total} tender(s) missing a date...")
        session = requests.Session()
        updated = 0
        for i, tender in enumerate(qs.iterator(), start=1):
            published_at, submission_deadline = fetch_notice_dates(session, tender.external_id)
            if published_at is not None or submission_deadline is not None:
                Tender.objects.filter(pk=tender.pk).update(
                    published_at=published_at, submission_deadline=submission_deadline
                )
                updated += 1
            if i % 25 == 0 or i == total:
                self.stdout.write(f"  [{i}/{total}]")
            time.sleep(OE_REQUEST_DELAY_SECONDS)
        self.stdout.write(self.style.SUCCESS(f"oeffentlichevergabe.de: {updated}/{total} updated.\n"))

    def _backfill_ted(self, qs) -> None:
        external_ids = list(qs.values_list("external_id", flat=True))
        total = len(external_ids)
        self.stdout.write(f"TED: {total} tender(s) missing a date...")
        updated = 0
        session = requests.Session()

        for start in range(0, total, TED_BATCH_SIZE):
            batch = external_ids[start : start + TED_BATCH_SIZE]
            query = "publication-number IN (" + ", ".join(batch) + ")"
            resp = session.post(
                TED_SEARCH_URL,
                json={
                    "query": query,
                    "fields": ["publication-number", "publication-date", "deadline-receipt-tender-date-lot"],
                    "page": 1,
                    "limit": TED_BATCH_SIZE,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            for notice in resp.json().get("notices", []):
                pub_number = notice.get("publication-number")
                if not pub_number:
                    continue
                Tender.objects.filter(external_id=pub_number).update(
                    published_at=_ted_to_date(notice.get("publication-date")),
                    submission_deadline=_earliest_date(notice.get("deadline-receipt-tender-date-lot")),
                )
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"TED: {updated}/{total} updated.\n"))

    def _backfill_from_cleaned_csv(self, qs) -> None:
        total = qs.count()
        self.stdout.write(f"Other sources (clean_data CSV): {total} tender(s) missing a date...")
        notice_csv = CLEANED_DIR / "notice_clean.csv"
        if not notice_csv.exists():
            self.stdout.write(self.style.WARNING(f"  {notice_csv} not found, skipping."))
            return

        notice = pd.read_csv(notice_csv, dtype={"noticeIdentifier": str, "noticeVersion": str}, low_memory=False)
        notice["_ver"] = notice["noticeVersion"].astype(int)
        notice = notice.sort_values("_ver").drop_duplicates("noticeIdentifier", keep="last")
        published_by_id = dict(zip(notice["noticeIdentifier"], notice["publicationDate"]))

        updated = 0
        for tender in qs.iterator():
            raw = published_by_id.get(tender.external_id)
            published_at = _to_date(raw)
            if published_at is not None:
                Tender.objects.filter(pk=tender.pk).update(published_at=published_at)
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Other sources: {updated}/{total} updated (submission_deadline left null - "
                "not present in this dataset's raw tables)."
            )
        )


def _to_date(value) -> Optional[date]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return pd.Timestamp(value).date()
    except (ValueError, TypeError):
        return None
