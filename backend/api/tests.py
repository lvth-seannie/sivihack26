from decimal import Decimal as D
from unittest import TestCase

from django.test import TestCase as DjangoTestCase

from .engine import CANDIDATE, FLAG, HARD_FAIL, ScreenCompany, ScreenItem, evaluate
from .models import Company, Lot, Tender
from .services import run_screening, serialize_result

BRENNER = ScreenCompany(
    region_radius_km=D(80),
    contract_min=D(50_000),
    contract_max=D(2_000_000),
    guarantee_ceiling=D(100_000),
    references_held=["Tiefbau", "Kanalbau", "Straßenbau", "Abbrucharbeiten"],
    capabilities_excluded=["Elektroinstallation", "Abbrucharbeiten"],
)


class EvaluateTests(TestCase):
    """Pure rule-engine tests - no Django DB required."""

    def test_out_of_radius_hard_fails_first(self):
        item = ScreenItem(distance_km=D(95), value=D(100_000), references_required=["Tiefbau"])
        verdict, reason = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)
        self.assertEqual(reason, "Vượt bán kính hoạt động")

    def test_value_out_of_range(self):
        item = ScreenItem(distance_km=D(10), value=D(3_000_000))
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)

    def test_guarantee_over_ceiling(self):
        item = ScreenItem(distance_km=D(10), value=D(100_000), guarantee_required=D(150_000))
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)

    def test_missing_reference(self):
        item = ScreenItem(distance_km=D(10), value=D(100_000), references_required=["Fassadenbau"])
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)

    def test_excluded_capability_even_if_referenced(self):
        item = ScreenItem(distance_km=D(10), value=D(100_000), references_required=["Abbrucharbeiten"])
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)

    def test_guarantee_near_ceiling_flags(self):
        item = ScreenItem(distance_km=D(10), value=D(100_000), guarantee_required=D(95_000))
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, FLAG)

    def test_clean_tender_is_candidate(self):
        item = ScreenItem(distance_km=D(10), value=D(100_000), guarantee_required=D(10_000), references_required=["Tiefbau"])
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, CANDIDATE)


class ScreeningServiceTests(DjangoTestCase):
    """Requires a real database connection - run via `manage.py test` once
    Neon (or another Postgres) credentials are configured."""

    def setUp(self):
        self.company = Company.objects.create(
            name="Brenner & Sohn Tiefbau GmbH",
            region_center="Augsburg",
            region_radius_km=80,
            contract_min=50_000,
            contract_max=2_000_000,
            guarantee_ceiling=100_000,
            references_held=["Tiefbau", "Kanalbau"],
            capabilities_excluded=["Elektroinstallation"],
        )
        self.tender = Tender.objects.create(
            external_id="T-1",
            title="Too big for the tender, fine for a lot",
            distance_from_augsburg_km=5,
            contract_value=3_000_000,
            guarantee_required=50_000,
            references_required=["Tiefbau"],
        )
        Lot.objects.create(
            tender=self.tender,
            lot_number="1",
            value=200_000,
            guarantee_required=20_000,
            references_required=["Tiefbau"],
        )

    def test_lot_can_be_candidate_when_tender_hard_fails(self):
        run_screening(self.company)
        result = serialize_result(self.company)
        tender_out = result["tenders"][0]
        self.assertEqual(tender_out["verdict"], HARD_FAIL)
        self.assertEqual(tender_out["lots"][0]["verdict"], CANDIDATE)
        self.assertTrue(tender_out["lots"][0]["differs_from_tender"])

    def test_results_are_cached_between_calls(self):
        run_screening(self.company)
        first = serialize_result(self.company)
        second = serialize_result(self.company)
        self.assertEqual(first["generated_at"], second["generated_at"])
