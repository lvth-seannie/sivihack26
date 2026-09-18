from django.contrib.postgres.fields import ArrayField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255)
    region_center = models.CharField(max_length=255)
    # Geocoded by backfill_coordinates - null until then. Distance to a
    # tender is computed at evaluation time (see engine.py); a company or
    # tender missing coordinates is a FLAG ("can't verify"), never a
    # silent pass.
    region_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    region_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    region_radius_km = models.DecimalField(max_digits=8, decimal_places=2)
    contract_min = models.DecimalField(max_digits=14, decimal_places=2)
    contract_max = models.DecimalField(max_digits=14, decimal_places=2)
    guarantee_ceiling = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    # Some companies are bottlenecked by how many bids their estimating team
    # can chase per week, not by guarantee capital (e.g. a large GC that can
    # bond anything but can only seriously pursue ~3 tenders/week). Informational
    # only for now - not read by the rule engine (see engine.py note).
    weekly_bid_capacity = models.PositiveIntegerField(null=True, blank=True)
    references_held = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    capabilities_excluded = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    available_from = models.DateField(null=True, blank=True)

    # Descriptive profile fields (Appendix A) - not used by the rule engine,
    # shown in the UI so an estimator/bid manager can sanity-check a verdict
    # against who this company actually is.
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    employee_count = models.PositiveIntegerField(null=True, blank=True)
    revenue_eur = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    tagline = models.TextField(blank=True)
    can_show = ArrayField(models.CharField(max_length=500), default=list, blank=True)
    cannot_show = ArrayField(models.CharField(max_length=500), default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tender(models.Model):
    external_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=500)
    source_url = models.URLField(max_length=1000, blank=True)
    # When the notice was published, and when bids are due - two distinct
    # business dates, neither the same as extracted_at (our own pipeline
    # timestamp, never shown to users). Null when the source genuinely
    # never carried the value, not defaulted/guessed.
    published_at = models.DateField(null=True, blank=True)
    submission_deadline = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    contract_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    guarantee_required = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    references_required = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    construction_window = models.CharField(max_length=255, blank=True)
    cpv_code = models.CharField(max_length=50, blank=True)
    raw_document_key = models.CharField(max_length=500, blank=True)
    extracted_at = models.DateTimeField(null=True, blank=True)
    # Per-field {"guarantee_required": {"snippet": ..., "page": ...}, ...}
    # captured by the extraction step, keyed by the Tender field it backs.
    # engine.build_context() looks these up so a HARD_FAIL/FLAG reason can
    # quote its source instead of just naming the rule.
    source_citations = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)

    class Meta:
        ordering = ["-extracted_at", "-id"]

    def __str__(self):
        return self.title


class Lot(models.Model):
    tender = models.ForeignKey(Tender, related_name="lots", on_delete=models.CASCADE)
    lot_number = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    guarantee_required = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    references_required = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    source_citations = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)

    class Meta:
        ordering = ["lot_number"]

    def __str__(self):
        return f"{self.tender.title} — Lot {self.lot_number}"


class Verdict(models.Model):
    class VerdictType(models.TextChoices):
        HARD_FAIL = "HARD_FAIL", "Hard fail"
        FLAG = "FLAG", "Flag"
        CANDIDATE = "CANDIDATE", "Candidate"

    company = models.ForeignKey(Company, related_name="verdicts", on_delete=models.CASCADE)
    tender = models.ForeignKey(Tender, related_name="verdicts", on_delete=models.CASCADE)
    lot = models.ForeignKey(
        Lot, related_name="verdicts", null=True, blank=True, on_delete=models.CASCADE
    )
    verdict = models.CharField(max_length=20, choices=VerdictType.choices)
    # Stable rule key (e.g. "OUT_OF_RADIUS") + the language-neutral facts
    # behind it. The frontend renders both into a sentence in the viewer's
    # chosen language - nothing language-specific is stored here.
    reason_code = models.CharField(max_length=50, default="")
    context = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    source_page = models.PositiveIntegerField(null=True, blank=True)
    evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tender_id", "lot_id"]

    def __str__(self):
        target = f"Lot {self.lot.lot_number}" if self.lot_id else "Tender"
        return f"{self.company} · {self.tender} · {target} → {self.verdict}"
