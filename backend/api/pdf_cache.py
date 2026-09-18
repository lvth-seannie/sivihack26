"""Shared helper for caching an oeffentlichevergabe.de notice's own PDF to
B2. Used by both ingest_tenders.py (live daily-export discovery) and
fetch_tender_documents.py (backfill for tenders already in the DB without
a cached PDF yet) - same source, same B2 key scheme, one place to fix.
"""

import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional, Tuple

import fitz  # PyMuPDF
import requests
from django.core.files.base import ContentFile

from storage_client.client import delete_file, file_exists, upload_file

API_BASE = "https://oeffentlichevergabe.de"
REQUEST_TIMEOUT = 30

# UBL/eForms namespace URIs (not prefixes - some notices alias them to ns8:,
# ns2: etc. instead of the conventional cac:/cbc:, so lookups below use the
# full {uri}LocalName form, which works regardless of the alias used).
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"

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


def _parse_ubl_date(text: Optional[str]) -> Optional[date]:
    """UBL dates carry a timezone offset suffix ("2026-09-18+02:00") that
    date.fromisoformat() (Python < 3.11) can't parse directly - the date
    itself is always the first 10 characters."""
    if not text or len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def fetch_notice_dates(session: requests.Session, external_id: str) -> Tuple[Optional[date], Optional[date]]:
    """Returns (published_at, submission_deadline) for a notice, parsed from
    its raw eForms/UBL XML (the OCDS export used elsewhere in ingestion
    doesn't carry either date at all - see the audit in the git history for
    this function). Best-effort: returns (None, None) on any fetch/parse
    failure rather than raising, since a missing date must never block
    ingesting the rest of the tender."""

    try:
        resp = session.get(f"{API_BASE}/api/notices/{external_id}", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError):
        return None, None

    published_at = _parse_ubl_date((root.findtext(f"{{{_CBC}}}IssueDate") or "").strip() or None)

    deadline_el = root.find(f".//{{{_CAC}}}TenderSubmissionDeadlinePeriod/{{{_CBC}}}EndDate")
    submission_deadline = _parse_ubl_date(deadline_el.text.strip() if deadline_el is not None and deadline_el.text else None)

    return published_at, submission_deadline
