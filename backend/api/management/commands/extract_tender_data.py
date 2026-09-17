"""AI extraction step: reads a tender's cached PDF and fills in the
fields the rule engine actually needs (guarantee_required,
references_required, construction_window, per-lot requirements) that
ingestion/ETL deliberately leave blank - those come from the source
document's text, not structured notice metadata.

    python manage.py extract_tender_data --limit 5

Deliberately separate from ingest_tenders.py / load_cleaned_tenders.py /
fetch_tender_documents.py: this is the slow, expensive step (one LLM call
per tender), so it only runs against tenders that already have a cached
PDF, and is safe to re-run without re-downloading anything.
"""

import time
from decimal import Decimal
from typing import List, Optional

import fitz  # PyMuPDF
from django.core.management.base import BaseCommand
from django.utils import timezone
from pydantic import BaseModel

from ai_client.client import generate
from api.models import Lot, Tender
from storage_client.client import download_file

MAX_PAGES = 30
MAX_CHARS_PER_PAGE = 4000
REQUEST_DELAY_SECONDS = 1.0

SYSTEM_PROMPT = (
    "You are reading a German public construction tender document "
    "(Vergabeunterlagen) for a bid-screening tool used by construction "
    "companies. Extract ONLY facts that are actually stated in the text - "
    "never guess or infer a number that isn't written down. If a field "
    "isn't mentioned, leave it null (or an empty list). Keep reference/"
    "qualification labels (Referenzen, Fachlose, Gewerke) in their "
    "original German wording - don't translate them. Every non-null field "
    "you extract must have a matching entry in source_citations with the "
    "exact snippet (max ~200 characters, verbatim from the text) and the "
    "page number it came from (page may be null if you can't pin one down). "
    "Respond with ONLY a single JSON object - no markdown code fences, no "
    "explanation before or after it."
)

PROMPT_TEMPLATE = """Extract the bid-relevant requirements from this tender document.

Return a single JSON object with exactly these keys:
- guarantee_required: the required performance/bid bond amount in EUR, as a plain number (e.g. "Bietungsbürgschaft" or "Vertragserfüllungsbürgschaft"), or null if not stated.
- references_required: list of required proof-of-experience qualifications/reference project types (e.g. "Straßenbau", "Kanalbau"), or [] if none are specified.
- construction_window: the execution/construction period as a short human-readable string (e.g. dates or "Frühjahr 2027"), or null if not stated.
- lots: if the tender is split into lots ("Lose"/"Fachlose"), one entry per lot as {{"lot_number": int, "description": string, "value": number|null, "guarantee_required": number|null, "references_required": [string]}}. Empty list if the tender is not split into lots.
- source_citations: one entry per non-null field above, as {{"field": string, "snippet": string, "page": int|null}}.

--- DOCUMENT TEXT ({page_count} pages) ---
{text}
"""


class LotExtraction(BaseModel):
    lot_number: int
    description: str
    value: Optional[float] = None
    guarantee_required: Optional[float] = None
    references_required: List[str] = []


class Citation(BaseModel):
    field: str
    snippet: str
    page: Optional[int] = None


class TenderExtraction(BaseModel):
    guarantee_required: Optional[float] = None
    references_required: List[str] = []
    construction_window: Optional[str] = None
    lots: List[LotExtraction] = []
    source_citations: List[Citation] = []


def _to_decimal(value: Optional[float]) -> Optional[Decimal]:
    return None if value is None else Decimal(str(value))


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Page-annotated text ('--- Page N ---' markers) so the model can cite
    real page numbers. Truncates generously - long tender PDFs (annexes,
    boilerplate) rarely have new bid-relevant facts past the first ~30 pages."""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        parts = []
        for i, page in enumerate(doc):
            if i >= MAX_PAGES:
                break
            text = page.get_text()[:MAX_CHARS_PER_PAGE]
            parts.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(parts), min(len(doc), MAX_PAGES)
    finally:
        doc.close()


class Command(BaseCommand):
    help = "Extract guarantee/reference/lot requirements from cached tender PDFs via Claude."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20, help="Max number of tenders to process.")

    def handle(self, *args, **options):
        limit = options["limit"]
        tenders = list(
            Tender.objects.filter(extracted_at__isnull=True)
            .exclude(raw_document_key="")
            .order_by("id")[:limit]
        )
        total = len(tenders)

        if total == 0:
            self.stdout.write("Nothing to do - no un-extracted tenders with a cached PDF.")
            return

        self.stdout.write(f"Extracting {total} tender(s)...\n")

        failed_ids: List[str] = []
        succeeded = 0

        for i, tender in enumerate(tenders, start=1):
            self.stdout.write(f"[{i}/{total}] tender {tender.external_id} ... ", ending="")
            try:
                self._extract_one(tender)
                self.stdout.write(self.style.SUCCESS("ok"))
                succeeded += 1
            except Exception as exc:  # one bad tender must not kill the batch
                self.stdout.write(self.style.ERROR(f"FAILED ({exc})"))
                failed_ids.append(tender.external_id)
            time.sleep(REQUEST_DELAY_SECONDS)

        self.stdout.write(f"\nDone: {succeeded} succeeded, {len(failed_ids)} failed.")

        if failed_ids:
            with open("failed_extractions.log", "a") as f:
                for external_id in failed_ids:
                    f.write(f"{external_id}\n")
            self.stdout.write(self.style.WARNING("Failed tender IDs appended to failed_extractions.log"))

    def _extract_one(self, tender: Tender) -> None:
        pdf_bytes = download_file(tender.raw_document_key)
        text, page_count = _extract_pdf_text(pdf_bytes)

        result = generate(
            PROMPT_TEMPLATE.format(page_count=page_count, text=text),
            output_format=TenderExtraction,
            system=SYSTEM_PROMPT,
        )

        citations_by_field = {c.field: {"snippet": c.snippet, "page": c.page} for c in result.source_citations}

        tender.guarantee_required = _to_decimal(result.guarantee_required)
        tender.references_required = result.references_required
        tender.construction_window = result.construction_window or ""
        tender.source_citations = citations_by_field
        tender.extracted_at = timezone.now()
        tender.save(
            update_fields=[
                "guarantee_required",
                "references_required",
                "construction_window",
                "source_citations",
                "extracted_at",
            ]
        )

        existing_lots = list(tender.lots.order_by("id"))
        for idx, lot_data in enumerate(result.lots):
            if idx < len(existing_lots):
                lot = existing_lots[idx]
                lot.description = lot_data.description or lot.description
                if lot_data.value is not None:
                    lot.value = _to_decimal(lot_data.value)
                lot.guarantee_required = _to_decimal(lot_data.guarantee_required)
                lot.references_required = lot_data.references_required
                lot.save(update_fields=["description", "value", "guarantee_required", "references_required"])
            else:
                Lot.objects.create(
                    tender=tender,
                    lot_number=str(lot_data.lot_number),
                    description=lot_data.description,
                    value=_to_decimal(lot_data.value),
                    guarantee_required=_to_decimal(lot_data.guarantee_required),
                    references_required=lot_data.references_required,
                )
