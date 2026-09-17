from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Company, Lot, Tender


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


# Appendix A - three fictional companies, used close to the brief's own
# numbers. Reference/capability vocabulary is left in German on purpose:
# it's the terminology that appears in the source tender documents, and a
# German-speaking estimator recognizes it verbatim regardless of which UI
# language is selected. See engine.py for why reasons are codes, not text.
COMPANIES = [
    {
        "name": "Brenner & Sohn Tiefbau GmbH",
        "region_center": "Augsburg",
        "region_radius_km": 150,
        "contract_min": 400_000,
        "contract_max": 4_000_000,
        "guarantee_ceiling": 1_500_000,
        "references_held": ["Straßenbau", "Kanalbau", "Erdarbeiten", "Tiefbau", "Gleisbau"],
        "capabilities_excluded": ["Gleisbau", "Brückenbau"],
        "available_from": "2027-03-01",
        "founded_year": 1962,
        "employee_count": 140,
        "revenue_eur": 31_000_000,
        "description": (
            "Straßenbau, Kanal- und Rohrleitungsbau, Erdarbeiten, kommunaler Tiefbau. "
            "Eigener Maschinenpark. Familienunternehmen seit 1962."
        ),
        "tagline": (
            "Wir sind zuverlässig und lokal. Bei etwa der Hälfte der Ausschreibungen "
            "verlieren wir preislich gegen die Großen. Wir wollen die Aufträge, bei "
            "denen es dem Auftraggeber wichtig ist, dass wir zuverlässig da sind."
        ),
        "can_show": [
            "Staatsstraßensanierung, Auftragswert 2,9 Mio. €",
            "Erneuerung eines Kanalnetzes im Landkreis",
            "Mehrere Erschließungsmaßnahmen für Wohngebiete",
        ],
        "cannot_show": [
            "Gleisbau (keine DB-Qualifikation, kein zertifiziertes Sicherheitspersonal)",
            "Brückenbau",
            "Projekte außerhalb Deutschlands",
        ],
    },
    {
        "name": "Elektro Vogtland GmbH",
        "region_center": "Plauen",
        "region_radius_km": 200,
        "contract_min": 80_000,
        "contract_max": 900_000,
        "guarantee_ceiling": 300_000,
        "references_held": [
            "Elektroinstallation", "Beleuchtung", "Brandmeldeanlagen", "Gebäudeautomation", "Hochspannung",
        ],
        "capabilities_excluded": ["Hochspannung", "Ex-Schutz", "Generalunternehmer"],
        "available_from": "2026-01-01",
        "founded_year": 1991,
        "employee_count": 45,
        "revenue_eur": 8_000_000,
        "description": (
            "Elektroinstallation für Gebäude — Stark- und Schwachstrom, Beleuchtung, "
            "Brandmeldeanlagen, Gebäudeautomation. Meist als Nachunternehmer für "
            "Generalunternehmer."
        ),
        "tagline": (
            "Wir sind gut, aber klein. Die Ausschreibungsunterlagen sind der Grund, "
            "warum die meisten Aufträge über Generalunternehmer zu uns kommen. Ist "
            "eine öffentliche Ausschreibung unkompliziert, bieten wir auch direkt an."
        ),
        "can_show": [
            "Schulsanierungen (Elektro)",
            "Bettenhaus eines Krankenhauses",
            "Büroausbauten",
            "Zwei Pflegeheime",
        ],
        "cannot_show": [
            "Hochspannungsanlagen",
            "Ex-geschützte Installationen",
            "Generalunternehmerschaft bei gewerkeübergreifenden Projekten",
        ],
    },
    {
        "name": "Hanseatische Bau AG",
        "region_center": "Hamburg",
        "region_radius_km": 300,
        "contract_min": 8_000_000,
        "contract_max": 90_000_000,
        # Real constraint per the brief is estimating-team bid capacity, not
        # bonding capital - guarantee_ceiling is genuinely unknown/unbounded
        # for them, so rules 3/6 are skipped rather than guessed.
        "guarantee_ceiling": None,
        "weekly_bid_capacity": 3,
        "references_held": ["Hochbau", "Generalunternehmer", "Schlüsselfertigbau", "Wohnungsbau"],
        "capabilities_excluded": ["Straßenbau", "Kanalbau", "Brückenbau", "Tiefbau"],
        "available_from": None,
        "founded_year": 1954,
        "employee_count": 620,
        "revenue_eur": 310_000_000,
        "description": (
            "Hochbau und schlüsselfertige Projekte — Büros, Schulen, Krankenhäuser, "
            "Wohnungsbau, Logistik. Koordination durch eigenes Team, Gewerke im "
            "Nachunternehmereinsatz. Nicht das Kapital ist der limitierende Faktor, "
            "sondern die Kapazität der Kalkulationsabteilung: etwa drei ernsthaft "
            "verfolgte Ausschreibungen pro Woche."
        ),
        "tagline": (
            "Wir sind ein Koordinationsunternehmen. Was uns schadet, ist eine "
            "Ausschreibung mit hohem Eigenleistungsanteil — darauf sind wir nicht "
            "ausgelegt."
        ),
        "can_show": [
            "Neubau eines Universitätsgebäudes",
            "Zwei Schulcampus-Projekte",
            "Erweiterung eines Krankenhauses",
            "Große Wohnquartiere",
        ],
        "cannot_show": [
            "Tiefbau als Hauptauftragnehmer (Straßen, Kanäle, Brücken)",
            "Projekte in Süddeutschland (seit einem Jahrzehnt keine mehr)",
        ],
    },
]

PORTAL = "https://www.evergabe-online.de/tender"

TENDERS = [
    # --- Bavaria / Schwaben (Brenner & Sohn territory) ---
    {
        "external_id": "TND-2026-0101",
        "title": "Fahrbahnsanierung B300 Königsbrunn",
        "source_url": f"{PORTAL}/TND-2026-0101",
        "location": "Königsbrunn",
        "contract_value": 850_000,
        "guarantee_required": 60_000,
        "references_required": ["Straßenbau"],
        "construction_window": "Frühjahr 2027",
        "cpv_code": "45233120-6",
        "extracted_at": "2026-09-17T09:00:00",
        "lots": [
            {"lot_number": "1", "description": "Fahrbahnsanierung Hauptabschnitt", "value": 850_000, "guarantee_required": 60_000, "references_required": ["Straßenbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0102",
        "title": "Kanalsanierung Innenstadt Augsburg",
        "source_url": f"{PORTAL}/TND-2026-0102",
        "location": "Augsburg",
        "contract_value": 2_800_000,
        "guarantee_required": 1_410_000,
        "references_required": ["Kanalbau"],
        "construction_window": "Herbst 2026",
        "cpv_code": "45232400-6",
        "extracted_at": "2026-09-17T08:30:00",
        "lots": [
            {"lot_number": "1", "description": "Kanalsanierung Hauptstrang", "value": 2_800_000, "guarantee_required": 1_410_000, "references_required": ["Kanalbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0103",
        "title": "Erschließung Neubaugebiet Gersthofen",
        "source_url": f"{PORTAL}/TND-2026-0103",
        "location": "Gersthofen",
        "contract_value": 650_000,
        "guarantee_required": 45_000,
        "references_required": ["Erdarbeiten"],
        "construction_window": "2027",
        "cpv_code": "45111200-0",
        "extracted_at": "2026-09-16T14:00:00",
        "lots": [
            {"lot_number": "1", "description": "Erdarbeiten & Kanalanschluss", "value": 400_000, "guarantee_required": 28_000, "references_required": ["Erdarbeiten", "Kanalbau"]},
            {"lot_number": "2", "description": "Straßenbau Erschließungsstraße", "value": 250_000, "guarantee_required": 17_000, "references_required": ["Straßenbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0104",
        "title": "Sanierung Stadthalle Augsburg",
        "source_url": f"{PORTAL}/TND-2026-0104",
        "location": "Augsburg",
        "contract_value": 5_500_000,
        "guarantee_required": 300_000,
        "references_required": ["Hochbau"],
        "construction_window": "2027–2028",
        "cpv_code": "45454100-5",
        "extracted_at": "2026-09-16T11:00:00",
        "lots": [
            {"lot_number": "1", "description": "Fassaden- und Innenausbau", "value": 3_200_000, "guarantee_required": 180_000, "references_required": ["Hochbau"]},
            {"lot_number": "2", "description": "Tiefbauarbeiten Vorplatz & Kanalanschluss", "value": 900_000, "guarantee_required": 70_000, "references_required": ["Tiefbau", "Kanalbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0105",
        "title": "Radbrücke Lech-Querung Friedberg",
        "source_url": f"{PORTAL}/TND-2026-0105",
        "location": "Friedberg",
        "contract_value": 1_100_000,
        "guarantee_required": 90_000,
        "references_required": ["Brückenbau"],
        "construction_window": "2027",
        "cpv_code": "45221111-3",
        "extracted_at": "2026-09-15T10:00:00",
        "lots": [
            {"lot_number": "1", "description": "Brückenbau komplett", "value": 1_100_000, "guarantee_required": 90_000, "references_required": ["Brückenbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0106",
        "title": "Gleisanschluss Sanierung Neusäß",
        "source_url": f"{PORTAL}/TND-2026-0106",
        "location": "Neusäß",
        "contract_value": 780_000,
        "guarantee_required": 55_000,
        "references_required": ["Gleisbau"],
        "construction_window": "Q2 2027",
        "cpv_code": "45234115-5",
        "extracted_at": "2026-09-15T09:00:00",
        "lots": [
            {"lot_number": "1", "description": "Gleisanschluss & Sicherungstechnik", "value": 780_000, "guarantee_required": 55_000, "references_required": ["Gleisbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0107",
        "title": "Straßen- und Kanalbau Rosenheim",
        "source_url": f"{PORTAL}/TND-2026-0107",
        "location": "Rosenheim",
        "contract_value": 1_600_000,
        "guarantee_required": 110_000,
        "references_required": ["Straßenbau", "Kanalbau"],
        "construction_window": "2027",
        "cpv_code": "45233120-6",
        "extracted_at": "2026-09-14T09:00:00",
        "lots": [
            {"lot_number": "1", "description": "Straßen- und Kanalbau komplett", "value": 1_600_000, "guarantee_required": 110_000, "references_required": ["Straßenbau", "Kanalbau"]},
        ],
    },
    # --- Saxony / Thuringia / eastern Bavaria (Elektro Vogtland territory) ---
    {
        "external_id": "TND-2026-0201",
        "title": "Elektroinstallation Schulsanierung Plauen",
        "source_url": f"{PORTAL}/TND-2026-0201",
        "location": "Plauen",
        "contract_value": 320_000,
        "guarantee_required": 40_000,
        "references_required": ["Elektroinstallation"],
        "construction_window": "Sommer 2027",
        "cpv_code": "45315300-1",
        "extracted_at": "2026-09-17T07:30:00",
        "lots": [
            {"lot_number": "1", "description": "Elektroinstallation komplett", "value": 320_000, "guarantee_required": 40_000, "references_required": ["Elektroinstallation"]},
        ],
    },
    {
        "external_id": "TND-2026-0202",
        "title": "Brandmeldeanlage Klinikneubau Zwickau",
        "source_url": f"{PORTAL}/TND-2026-0202",
        "location": "Zwickau",
        "contract_value": 480_000,
        "guarantee_required": 285_000,
        "references_required": ["Brandmeldeanlagen"],
        "construction_window": "2027",
        "cpv_code": "45312100-8",
        "extracted_at": "2026-09-16T09:30:00",
        "lots": [
            {"lot_number": "1", "description": "Brandmeldeanlage komplett", "value": 480_000, "guarantee_required": 285_000, "references_required": ["Brandmeldeanlagen"]},
        ],
    },
    {
        "external_id": "TND-2026-0203",
        "title": "Büro- und Objektausbau Chemnitz",
        "source_url": f"{PORTAL}/TND-2026-0203",
        "location": "Chemnitz",
        "contract_value": 140_000,
        "guarantee_required": 18_000,
        "references_required": ["Elektroinstallation", "Beleuchtung"],
        "construction_window": "Q1 2027",
        "cpv_code": "45315100-9",
        "extracted_at": "2026-09-15T08:00:00",
        "lots": [
            {"lot_number": "1", "description": "Beleuchtung Bürotrakt", "value": 60_000, "guarantee_required": 8_000, "references_required": ["Beleuchtung"]},
            {"lot_number": "2", "description": "Gebäudeautomation Serverraum", "value": 80_000, "guarantee_required": 10_000, "references_required": ["Gebäudeautomation"]},
        ],
    },
    {
        "external_id": "TND-2026-0204",
        "title": "Umspannwerk Hochspannungsanlage Gera",
        "source_url": f"{PORTAL}/TND-2026-0204",
        "location": "Gera",
        "contract_value": 610_000,
        "guarantee_required": 150_000,
        "references_required": ["Hochspannung"],
        "construction_window": "2027",
        "cpv_code": "45232221-4",
        "extracted_at": "2026-09-14T10:30:00",
        "lots": [
            {"lot_number": "1", "description": "Hochspannungsanlage komplett", "value": 610_000, "guarantee_required": 150_000, "references_required": ["Hochspannung"]},
        ],
    },
    {
        "external_id": "TND-2026-0205",
        "title": "Elektro-Ausbau Verwaltungsgebäude Hof",
        "source_url": f"{PORTAL}/TND-2026-0205",
        "location": "Hof",
        "contract_value": 210_000,
        "guarantee_required": 25_000,
        "references_required": ["Elektroinstallation"],
        "construction_window": "Winter 2026/2027",
        "cpv_code": "45315300-1",
        "extracted_at": "2026-09-13T09:00:00",
        "lots": [
            {"lot_number": "1", "description": "Elektro-Ausbau komplett", "value": 210_000, "guarantee_required": 25_000, "references_required": ["Elektroinstallation"]},
        ],
    },
    # --- Northern Germany (Hanseatische Bau territory) ---
    {
        "external_id": "TND-2026-0301",
        "title": "Schulcampus Neubau Hamburg",
        "source_url": f"{PORTAL}/TND-2026-0301",
        "location": "Hamburg",
        "contract_value": 22_000_000,
        "guarantee_required": 1_800_000,
        "references_required": ["Generalunternehmer", "Schlüsselfertigbau"],
        "construction_window": "2027–2029",
        "cpv_code": "45210000-2",
        "extracted_at": "2026-09-17T06:45:00",
        "lots": [
            {"lot_number": "1", "description": "Campus Nord", "value": 11_000_000, "guarantee_required": 900_000, "references_required": ["Generalunternehmer", "Schlüsselfertigbau"]},
            {"lot_number": "2", "description": "Campus Süd", "value": 11_000_000, "guarantee_required": 900_000, "references_required": ["Generalunternehmer", "Schlüsselfertigbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0302",
        "title": "Bürogebäude Sanierung Bremen",
        "source_url": f"{PORTAL}/TND-2026-0302",
        "location": "Bremen",
        "contract_value": 12_500_000,
        "guarantee_required": 900_000,
        "references_required": ["Hochbau", "Generalunternehmer"],
        "construction_window": "2027",
        "cpv_code": "45454100-5",
        "extracted_at": "2026-09-16T07:00:00",
        "lots": [
            {"lot_number": "1", "description": "Sanierung komplett", "value": 12_500_000, "guarantee_required": 900_000, "references_required": ["Hochbau", "Generalunternehmer"]},
        ],
    },
    {
        "external_id": "TND-2026-0303",
        "title": "Straßen- und Kanalbauprojekt Hamburg-Nord",
        "source_url": f"{PORTAL}/TND-2026-0303",
        "location": "Hamburg",
        "contract_value": 9_500_000,
        "guarantee_required": 700_000,
        "references_required": ["Straßenbau", "Kanalbau"],
        "construction_window": "2027–2028",
        "cpv_code": "45233120-6",
        "extracted_at": "2026-09-14T06:30:00",
        "lots": [
            {"lot_number": "1", "description": "Straßen- und Kanalbau komplett", "value": 9_500_000, "guarantee_required": 700_000, "references_required": ["Straßenbau", "Kanalbau"]},
        ],
    },
    {
        "external_id": "TND-2026-0304",
        "title": "Klinikneubau Lübeck",
        "source_url": f"{PORTAL}/TND-2026-0304",
        "location": "Lübeck",
        "contract_value": 95_000_000,
        "guarantee_required": 4_000_000,
        "references_required": ["Generalunternehmer", "Schlüsselfertigbau"],
        "construction_window": "2028–2031",
        "cpv_code": "45210000-2",
        "extracted_at": "2026-09-13T07:00:00",
        "lots": [
            {"lot_number": "1", "description": "Rohbau & Fassade", "value": 45_000_000, "guarantee_required": 2_000_000, "references_required": ["Generalunternehmer"]},
            {"lot_number": "2", "description": "Medizintechnik & Ausstattung", "value": 15_000_000, "guarantee_required": 1_200_000, "references_required": ["Medizintechnik"]},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the 3 Appendix A companies and a geographically diverse sample tender set."

    @transaction.atomic
    def handle(self, *args, **options):
        # Only the 3 Appendix A companies ever live in this table, so a
        # full replace is safe here (and cascades to delete their
        # verdicts). Tenders/lots use update_or_create below instead of a
        # blanket delete, since real tenders from load_cleaned_tenders /
        # ingest_tenders share this same table and must survive a reseed.
        Company.objects.all().delete()
        for data in COMPANIES:
            Company.objects.create(**data)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(COMPANIES)} companies"))

        lot_count = 0
        for data in TENDERS:
            lots = data.pop("lots")
            external_id = data.pop("external_id")
            data["extracted_at"] = _dt(data["extracted_at"])
            tender, _ = Tender.objects.update_or_create(external_id=external_id, defaults=data)
            for lot_data in lots:
                lot_number = lot_data.pop("lot_number")
                Lot.objects.update_or_create(tender=tender, lot_number=lot_number, defaults=lot_data)
                lot_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(TENDERS)} tenders, {lot_count} lots"))
