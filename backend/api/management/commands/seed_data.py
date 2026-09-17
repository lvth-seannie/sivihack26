from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Company, Lot, Tender, Verdict


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


COMPANIES = [
    {
        "name": "Brenner & Sohn Tiefbau GmbH",
        "region_center": "Augsburg",
        "region_radius_km": 80,
        "contract_min": 50_000,
        "contract_max": 2_000_000,
        "guarantee_ceiling": 100_000,
        "references_held": [
            "Tiefbau", "Kanalbau", "Straßenbau", "Erdarbeiten", "Brückenbau", "Abbrucharbeiten",
        ],
        "capabilities_excluded": ["Elektroinstallation", "Photovoltaik", "Abbrucharbeiten"],
        "available_from": "2026-01-15",
    },
    {
        "name": "Elektro Vogtland GmbH",
        "region_center": "Augsburg",
        "region_radius_km": 45,
        "contract_min": 10_000,
        "contract_max": 300_000,
        "guarantee_ceiling": 30_000,
        "references_held": ["Elektroinstallation", "Photovoltaik", "Netzanschluss", "Beleuchtung"],
        "capabilities_excluded": ["Tiefbau", "Abbrucharbeiten", "Hochbau"],
        "available_from": "2026-02-01",
    },
    {
        "name": "Hanseatische Bau AG",
        "region_center": "Augsburg",
        "region_radius_km": 220,
        "contract_min": 200_000,
        "contract_max": 10_000_000,
        "guarantee_ceiling": 500_000,
        "references_held": [
            "Hochbau", "Tiefbau", "Fassadenbau", "Generalunternehmer", "Brückenbau", "Straßenbau",
        ],
        "capabilities_excluded": ["Elektroinstallation", "Photovoltaik"],
        "available_from": "2026-01-01",
    },
]

TENDERS = [
    {
        "external_id": "TND-2026-0091",
        "title": "Neubau Radweg B17 Augsburg–Königsbrunn",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0091",
        "location": "Königsbrunn",
        "distance_from_augsburg_km": 15,
        "contract_value": 180_000,
        "guarantee_required": 9_000,
        "references_required": ["Straßenbau"],
        "construction_window": "März–Juni 2027",
        "cpv_code": "45233120-6",
        "raw_document_key": "tenders/TND-2026-0091.pdf",
        "extracted_at": "2026-09-17T09:00:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "Radwegbau Hauptabschnitt",
                "value": 180_000,
                "guarantee_required": 9_000,
                "references_required": ["Straßenbau"],
            },
        ],
    },
    {
        "external_id": "TND-2026-0092",
        "title": "Erweiterung Photovoltaikanlage Gewerbepark Friedberg",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0092",
        "location": "Friedberg",
        "distance_from_augsburg_km": 25,
        "contract_value": 145_000,
        "guarantee_required": 25_000,
        "references_required": ["Photovoltaik", "Elektroinstallation"],
        "construction_window": "Jan–März 2027",
        "cpv_code": "45315300-1",
        "raw_document_key": "tenders/TND-2026-0092.pdf",
        "extracted_at": "2026-09-17T08:30:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "PV-Module Montage",
                "value": 90_000,
                "guarantee_required": 15_000,
                "references_required": ["Photovoltaik"],
            },
            {
                "lot_number": "2",
                "description": "Elektroanschluss & Netzeinspeisung",
                "value": 55_000,
                "guarantee_required": 10_000,
                "references_required": ["Elektroinstallation", "Netzanschluss"],
            },
        ],
    },
    {
        "external_id": "TND-2026-0093",
        "title": "Sanierung Stadthalle Augsburg",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0093",
        "location": "Augsburg",
        "distance_from_augsburg_km": 3,
        "contract_value": 3_500_000,
        "guarantee_required": 180_000,
        "references_required": ["Hochbau", "Fassadenbau"],
        "construction_window": "2027–2028",
        "cpv_code": "45454100-5",
        "raw_document_key": "tenders/TND-2026-0093.pdf",
        "extracted_at": "2026-09-16T14:00:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "Fassadensanierung",
                "value": 1_200_000,
                "guarantee_required": 60_000,
                "references_required": ["Fassadenbau"],
            },
            {
                "lot_number": "2",
                "description": "Tiefbauarbeiten Vorplatz & Kanalanschluss",
                "value": 380_000,
                "guarantee_required": 40_000,
                "references_required": ["Tiefbau", "Kanalbau"],
            },
        ],
    },
    {
        "external_id": "TND-2026-0094",
        "title": "Kanalsanierung Innenstadt Augsburg",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0094",
        "location": "Augsburg",
        "distance_from_augsburg_km": 4,
        "contract_value": 620_000,
        "guarantee_required": 95_000,
        "references_required": ["Kanalbau", "Tiefbau"],
        "construction_window": "Herbst 2026",
        "cpv_code": "45232400-6",
        "raw_document_key": "tenders/TND-2026-0094.pdf",
        "extracted_at": "2026-09-15T11:00:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "Kanalsanierung Hauptstrang",
                "value": 620_000,
                "guarantee_required": 95_000,
                "references_required": ["Kanalbau", "Tiefbau"],
            },
        ],
    },
    {
        "external_id": "TND-2026-0095",
        "title": "Neubau Trafostation & Netzanschluss Gersthofen",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0095",
        "location": "Gersthofen",
        "distance_from_augsburg_km": 10,
        "contract_value": 68_000,
        "guarantee_required": 27_000,
        "references_required": ["Elektroinstallation", "Netzanschluss"],
        "construction_window": "Nov 2026–Jan 2027",
        "cpv_code": "45315100-9",
        "raw_document_key": "tenders/TND-2026-0095.pdf",
        "extracted_at": "2026-09-15T09:30:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "Trafostation & Netzanschluss komplett",
                "value": 68_000,
                "guarantee_required": 27_000,
                "references_required": ["Elektroinstallation", "Netzanschluss"],
            },
        ],
    },
    {
        "external_id": "TND-2026-0096",
        "title": "Rückbau ehemalige Lagerhalle Neusäß",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0096",
        "location": "Neusäß",
        "distance_from_augsburg_km": 8,
        "contract_value": 210_000,
        "guarantee_required": 18_000,
        "references_required": ["Abbrucharbeiten"],
        "construction_window": "Q1 2027",
        "cpv_code": "45111100-9",
        "raw_document_key": "tenders/TND-2026-0096.pdf",
        "extracted_at": "2026-09-14T10:00:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "Abbruch & Entsorgung Lagerhalle",
                "value": 210_000,
                "guarantee_required": 18_000,
                "references_required": ["Abbrucharbeiten"],
            },
        ],
    },
    {
        "external_id": "TND-2026-0097",
        "title": "Kläranlage Modernisierung Kempten",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0097",
        "location": "Kempten",
        "distance_from_augsburg_km": 95,
        "contract_value": 450_000,
        "guarantee_required": 35_000,
        "references_required": ["Tiefbau"],
        "construction_window": "2027",
        "cpv_code": "45252127-4",
        "raw_document_key": "tenders/TND-2026-0097.pdf",
        "extracted_at": "2026-09-14T08:00:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "Klärbecken Modernisierung komplett",
                "value": 450_000,
                "guarantee_required": 35_000,
                "references_required": ["Tiefbau"],
            },
        ],
    },
    {
        "external_id": "TND-2026-0098",
        "title": "Brückensanierung A995 Rosenheim",
        "source_url": "https://vergabe.bayern.de/tender/TND-2026-0098",
        "location": "Rosenheim",
        "distance_from_augsburg_km": 240,
        "contract_value": 1_800_000,
        "guarantee_required": 150_000,
        "references_required": ["Brückenbau"],
        "construction_window": "2027–2028",
        "cpv_code": "45221111-3",
        "raw_document_key": "tenders/TND-2026-0098.pdf",
        "extracted_at": "2026-09-13T15:00:00",
        "lots": [
            {
                "lot_number": "1",
                "description": "Brückenüberbau Sanierung",
                "value": 1_000_000,
                "guarantee_required": 90_000,
                "references_required": ["Brückenbau"],
            },
            {
                "lot_number": "2",
                "description": "Verkehrssicherung & Provisorium",
                "value": 800_000,
                "guarantee_required": 60_000,
                "references_required": ["Straßenbau"],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the 3 demo companies and sample tenders/lots for local testing."

    @transaction.atomic
    def handle(self, *args, **options):
        Verdict.objects.all().delete()
        Lot.objects.all().delete()
        Tender.objects.all().delete()
        Company.objects.all().delete()

        for data in COMPANIES:
            Company.objects.create(**data)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(COMPANIES)} companies"))

        lot_count = 0
        for data in TENDERS:
            lots = data.pop("lots")
            data["extracted_at"] = _dt(data["extracted_at"])
            tender = Tender.objects.create(**data)
            for lot_data in lots:
                Lot.objects.create(tender=tender, **lot_data)
                lot_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(TENDERS)} tenders, {lot_count} lots"))
