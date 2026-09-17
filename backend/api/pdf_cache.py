"""Shared helper for caching an oeffentlichevergabe.de notice's own PDF to
B2. Used by both ingest_tenders.py (live daily-export discovery) and
fetch_tender_documents.py (backfill for tenders already in the DB without
a cached PDF yet) - same source, same B2 key scheme, one place to fix.
"""

import fitz  # PyMuPDF
import requests
from django.core.files.base import ContentFile

from storage_client.client import delete_file, file_exists, upload_file

API_BASE = "https://oeffentlichevergabe.de"
REQUEST_TIMEOUT = 30

# oeffentlichevergabe.de's PDF renderer can't preview every eForms version
# (observed for many eForms-DE 1.2 notices, forms E1-E6) - it still returns
# HTTP 200, but the "PDF" is just this one-page German error notice instead
# of the actual document. Treat it as a fetch failure, not a cached document,
# so extraction never wastes a call on it and B2 doesn't fill up with
# placeholders.
_RENDER_ERROR_SIGNATURE = "Bei der Generierung der Vorschau ist ein Fehler aufgetreten"


class PdfRenderError(Exception):
    """Raised when oeffentlichevergabe.de returned its rendering-error
    placeholder instead of the actual notice PDF."""


def cache_notice_pdf(session: requests.Session, external_id: str) -> str:
    """Downloads the notice's own rendered PDF and uploads it to B2,
    returning the raw_document_key. Overwrites any existing object at that
    key via storage_client's own exists/delete, so this is safe to re-run.
    """

    resp = session.get(
        f"{API_BASE}/api/notices/{external_id}",
        params={"format": "pdf"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    doc = fitz.open(stream=resp.content, filetype="pdf")
    try:
        first_page_text = doc[0].get_text() if len(doc) else ""
    finally:
        doc.close()
    if _RENDER_ERROR_SIGNATURE in first_page_text:
        raise PdfRenderError(f"oeffentlichevergabe.de could not render a PDF for notice {external_id}")

    key = f"tenders/{external_id}.pdf"
    if file_exists(key):
        delete_file(key)
    upload_file(ContentFile(resp.content), key)
    return key
