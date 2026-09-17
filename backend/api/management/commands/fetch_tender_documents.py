"""Backfill: cache the notice PDF for every tender that doesn't have one
yet (e.g. rows loaded by load_cleaned_tenders, which only has metadata,
not documents) - reuses the exact same fetch-and-upload approach proven
in ingest_tenders.py, via the shared api.pdf_cache.cache_notice_pdf().

    python manage.py fetch_tender_documents --limit 5
"""

import time

import requests
from django.core.management.base import BaseCommand

from api.models import Tender
from api.pdf_cache import cache_notice_pdf

REQUEST_DELAY_SECONDS = 1.5


class Command(BaseCommand):
    help = "Fetch and cache the notice PDF (to B2) for tenders missing a raw_document_key."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Max number of tenders to process.")

    def handle(self, *args, **options):
        limit = options["limit"]
        tenders = list(Tender.objects.filter(raw_document_key="").order_by("id")[:limit])
        total = len(tenders)

        if total == 0:
            self.stdout.write("Nothing to do - every tender already has a raw_document_key.")
            return

        self.stdout.write(f"Fetching documents for {total} tender(s)...\n")

        session = requests.Session()
        failed_ids: list[str] = []
        succeeded = 0

        for i, tender in enumerate(tenders, start=1):
            self.stdout.write(f"[{i}/{total}] tender {tender.external_id} ... ", ending="")
            try:
                raw_document_key = cache_notice_pdf(session, tender.external_id)
                tender.raw_document_key = raw_document_key
                tender.save(update_fields=["raw_document_key"])
                self.stdout.write(self.style.SUCCESS("ok"))
                succeeded += 1
            except Exception as exc:  # one bad tender must not kill the batch
                self.stdout.write(self.style.ERROR(f"FAILED ({exc})"))
                failed_ids.append(tender.external_id)
            time.sleep(REQUEST_DELAY_SECONDS)

        self.stdout.write(f"\nDone: {succeeded} succeeded, {len(failed_ids)} failed.")

        if failed_ids:
            with open("failed_downloads.log", "a") as f:
                for external_id in failed_ids:
                    f.write(f"{external_id}\n")
            self.stdout.write(self.style.WARNING("Failed tender IDs appended to failed_downloads.log"))
