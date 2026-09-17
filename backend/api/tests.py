from decimal import Decimal as D
from unittest import TestCase

from django.test import TestCase as DjangoTestCase

from .engine import (
    CANDIDATE,
    FLAG,
    HARD_FAIL,
    REASON_CAPABILITY_EXCLUDED,
    REASON_OUT_OF_RADIUS,
    ScreenCompany,
    ScreenItem,
    evaluate,
)
from .models import Company, Lot, Tender
from .services import run_screening, serialize_result

BRENNER = ScreenCompany(
    region_radius_km=D(150),
    contract_min=D(400_000),
    contract_max=D(4_000_000),
    guarantee_ceiling=D(1_500_000),
    references_held=["Straßenbau", "Kanalbau", "Erdarbeiten", "Tiefbau", "Gleisbau"],
    capabilities_excluded=["Gleisbau"],
)


class EvaluateTests(TestCase):
    """Pure rule-engine tests - no Django DB required."""

    def test_out_of_radius_hard_fails_first(self):
        item = ScreenItem(distance_km=D(180), value=D(1_000_000), references_required=["Tiefbau"])
        verdict, reason_code = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)
        self.assertEqual(reason_code, REASON_OUT_OF_RADIUS)

    def test_value_out_of_range(self):
        item = ScreenItem(distance_km=D(10), value=D(5_000_000))
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)

    def test_guarantee_over_ceiling(self):
        item = ScreenItem(distance_km=D(10), value=D(1_000_000), guarantee_required=D(1_600_000))
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)

    def test_missing_reference(self):
        item = ScreenItem(distance_km=D(10), value=D(1_000_000), references_required=["Hochbau"])
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)

    def test_excluded_capability_even_if_referenced(self):
        item = ScreenItem(distance_km=D(10), value=D(1_000_000), references_required=["Gleisbau"])
        verdict, reason_code = evaluate(item, BRENNER)
        self.assertEqual(verdict, HARD_FAIL)
        self.assertEqual(reason_code, REASON_CAPABILITY_EXCLUDED)

    def test_guarantee_near_ceiling_flags(self):
        item = ScreenItem(distance_km=D(10), value=D(1_000_000), guarantee_required=D(1_400_000))
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, FLAG)

    def test_clean_tender_is_candidate(self):
        item = ScreenItem(
            distance_km=D(10), value=D(1_000_000), guarantee_required=D(100_000), references_required=["Tiefbau"]
        )
        verdict, _ = evaluate(item, BRENNER)
        self.assertEqual(verdict, CANDIDATE)


class ScreeningServiceTests(DjangoTestCase):
    """Requires a real database connection - run via `manage.py test` once
    Neon (or another Postgres) credentials are configured."""

    def setUp(self):
        self.company = Company.objects.create(
            name="Brenner & Sohn Tiefbau GmbH",
            region_center="Augsburg",
            region_radius_km=150,
            contract_min=400_000,
            contract_max=4_000_000,
            guarantee_ceiling=1_500_000,
            references_held=["Tiefbau", "Kanalbau"],
            capabilities_excluded=["Hochbau"],
        )
        self.tender = Tender.objects.create(
            external_id="T-1",
            title="Too big for the tender, fine for a lot",
            location="Augsburg",
            contract_value=5_000_000,
            guarantee_required=200_000,
            references_required=["Tiefbau"],
        )
        Lot.objects.create(
            tender=self.tender,
            lot_number="1",
            value=900_000,
            guarantee_required=60_000,
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
