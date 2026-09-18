"""ETL: load the teammate's cleaned TED/eForms CSV export into the Django
`tenders`/`lots` tables.

Source: backend/database/clean_data/*.csv, produced by
database/data_cleaning.py (already run - this command only joins and loads
what's there, it doesn't touch raw_data/ itself).

The cleaned CSVs are still one-file-per-eForms-table (not joined) - see
that script's own docstring. The join keys are (noticeIdentifier,
noticeVersion), with an optional lotIdentifier for lot-scoped rows (see
schema.sql's header comment for the full data model this is drawn from).

Only genuinely open calls for bids are loaded (formType == "competition" -
excludes award/result/modification/correction notices, which aren't
tenders a company could bid on), filtered to CPV codes starting "45"
(construction), matching the rest of this project's scope.

Extraction-dependent fields (guarantee_required, references_required,
construction_window) are intentionally left blank here - that's the job
of extract_tender_data, which reads the cached PDF, not this ETL.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Lot, Tender

CLEANED_DIR = Path(settings.BASE_DIR) / "database" / "clean_data"
NOTICE_UI_URL = "https://oeffentlichevergabe.de/ui/de/notice/{id}"
KEY_DTYPE = {"noticeIdentifier": str, "noticeVersion": str, "lotIdentifier": str}


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(CLEANED_DIR / name, dtype=KEY_DTYPE, low_memory=False)


def _to_decimal(value) -> Optional[Decimal]:
    if value is None or pd.isna(value):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_date(value) -> Optional[date]:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date()


class Command(BaseCommand):
    help = "Load the cleaned TED/eForms CSV export (database/clean_data/) into the tenders/lots tables."

    def handle(self, *args, **options):
        if not CLEANED_DIR.exists():
            self.stderr.write(self.style.ERROR(f"Cleaned data directory not found: {CLEANED_DIR}"))
            return

        notice = _read("notice_clean.csv")
        classification = _read("classification_clean.csv")
        purpose = _read("purpose_clean.csv")
        place = _read("placeOfPerformance_clean.csv")
        org = _read("organisation_clean.csv")
        lot_index = _read("lot_clean.csv")

        # One row per noticeIdentifier: keep the latest version only.
        notice = notice.copy()
        notice["_ver"] = notice["noticeVersion"].astype(int)
        notice = notice.sort_values("_ver").drop_duplicates("noticeIdentifier", keep="last")
        notice = notice[notice["formType"] == "competition"]

        cpv = classification[
            (classification["classificationType"] == "cpv") & (classification["lotIdentifier"].isna())
        ]
        cpv45 = cpv[cpv["mainClassificationCode"].str.startswith("45", na=False)]
        cpv45 = cpv45.drop_duplicates(["noticeIdentifier", "noticeVersion"], keep="first")

        notice_purpose = purpose[purpose["lotIdentifier"].isna()]
        notice_place = place[place["lotIdentifier"].isna()].drop_duplicates(
            ["noticeIdentifier", "noticeVersion"], keep="first"
        )
        buyers = org[org["organisationRole"] == "buyer"].drop_duplicates(
            ["noticeIdentifier", "noticeVersion"], keep="first"
        )

        keys = ["noticeIdentifier", "noticeVersion"]
        merged = (
            notice.merge(cpv45[keys + ["mainClassificationCode"]], on=keys, how="inner")
            .merge(notice_purpose[keys + ["title", "estimatedValue", "estimatedValueCurrency"]], on=keys, how="left")
            .merge(notice_place[keys + ["placePerformanceCity"]], on=keys, how="left")
            .merge(buyers[keys + ["organisationCity"]], on=keys, how="left")
        )

        self.stdout.write(f"{len(merged)} open construction (CPV 45xxx) notices matched.\n")

        inserted = updated = errored = 0
        matched_notice_keys = set()

        for row in merged.itertuples(index=False):
            try:
                notice_id = row.noticeIdentifier
                notice_ver = row.noticeVersion
                matched_notice_keys.add((notice_id, notice_ver))

                title = (row.title if isinstance(row.title, str) else "") or ""
                location = row.placePerformanceCity
                if not isinstance(location, str) or not location:
                    location = row.organisationCity if isinstance(row.organisationCity, str) else ""

                contract_value = None
                if row.estimatedValueCurrency == "EUR":
                    contract_value = _to_decimal(row.estimatedValue)

                tender, created = Tender.objects.update_or_create(
                    external_id=notice_id,
                    defaults={
                        "title": title[:500],
                        "source_url": NOTICE_UI_URL.format(id=notice_id),
                        "location": location[:255],
                        "contract_value": contract_value,
                        "cpv_code": row.mainClassificationCode,
                        # No submission deadline: this raw dataset's tables
                        # never carry it (confirmed by inspecting every
                        # raw_data/*.csv header) - left null, not guessed.
                        "published_at": _to_date(row.publicationDate),
                    },
                )
                self._load_lots(tender, lot_index, purpose, notice_id, notice_ver)
                inserted += created
                updated += not created
            except Exception as exc:  # one bad row must not kill the batch
                errored += 1
                self.stdout.write(self.style.ERROR(f"  skipped {row.noticeIdentifier}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nDone: {inserted} inserted, {updated} updated, {errored} skipped.")
        )

    def _load_lots(self, tender: Tender, lot_index: pd.DataFrame, purpose: pd.DataFrame, notice_id: str, notice_ver: str) -> None:
        lots = lot_index[
            (lot_index["noticeIdentifier"] == notice_id) & (lot_index["noticeVersion"] == notice_ver)
        ]
        lot_purpose = purpose[
            (purpose["noticeIdentifier"] == notice_id)
            & (purpose["noticeVersion"] == notice_ver)
            & (purpose["lotIdentifier"].notna())
        ]

        for lot_row in lots.itertuples(index=False):
            lot_number = lot_row.lotIdentifier
            match = lot_purpose[lot_purpose["lotIdentifier"] == lot_number]
            description = ""
            value = None
            if not match.empty:
                title = match.iloc[0]["title"]
                description = title if isinstance(title, str) else ""
                if match.iloc[0].get("estimatedValueCurrency") == "EUR":
                    value = _to_decimal(match.iloc[0]["estimatedValue"])

            Lot.objects.update_or_create(
                tender=tender,
                lot_number=lot_number,
                defaults={"description": description[:2000], "value": value},
            )
