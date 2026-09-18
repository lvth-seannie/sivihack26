"""One-time backfill: geocode every Company.region_center and distinct
Tender.location into lat/lng, so engine.py can compute distance dynamically
at evaluation time instead of relying on a per-tender precomputed column.

    python manage.py backfill_coordinates

Safe to re-run: only rows still missing coordinates are looked up again
(already-resolved rows are skipped, so a partial run - e.g. interrupted
mid-way through a large batch - just picks up where it left off without
re-spending the Nominatim rate-limit budget on rows already done).

Unresolved location strings are appended to unresolved_locations.log for
manual review - never silently defaulted to 0km or skipped, since a
tender with an unverifiable location must FLAG in the rule engine, not
silently pass as CANDIDATE (see REASON_LOCATION_UNVERIFIED in engine.py).
"""

from django.core.management.base import BaseCommand

from api import geo
from api.models import Company, Tender


class Command(BaseCommand):
    help = "Geocode Company.region_center and Tender.location into lat/lng for distance-at-evaluation-time."

    def handle(self, *args, **options):
        unresolved: list[str] = []

        self.stdout.write("Geocoding companies...")
        for company in Company.objects.filter(region_lat__isnull=True):
            coords = geo.geocode(company.region_center)
            if coords:
                company.region_lat, company.region_lng = coords
                company.save(update_fields=["region_lat", "region_lng"])
                self.stdout.write(f"  {company.name} ({company.region_center}) -> {coords}")
            else:
                unresolved.append(f"COMPANY:{company.name}:{company.region_center}")
                self.stdout.write(self.style.WARNING(f"  {company.name} ({company.region_center}) -> unresolved"))

        # order_by() clears Tender.Meta's default ordering (-extracted_at, -id) -
        # left in place, Django/Postgres folds those columns into the DISTINCT
        # comparison too, so it stops deduping by location alone.
        locations = list(
            Tender.objects.exclude(location="")
            .filter(location_lat__isnull=True)
            .order_by()
            .values_list("location", flat=True)
            .distinct()
        )
        self.stdout.write(f"\nGeocoding {len(locations)} distinct tender location(s)...")

        location_coords: dict[str, tuple] = {}
        for i, loc in enumerate(locations, start=1):
            coords = geo.geocode(loc)
            if coords:
                location_coords[loc] = coords
                self.stdout.write(f"  [{i}/{len(locations)}] {loc} -> {coords}")
            else:
                unresolved.append(f"TENDER_LOCATION:{loc}")
                self.stdout.write(self.style.WARNING(f"  [{i}/{len(locations)}] {loc} -> unresolved"))

        updated = 0
        for loc, (lat, lng) in location_coords.items():
            updated += Tender.objects.filter(location=loc, location_lat__isnull=True).update(
                location_lat=lat, location_lng=lng
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone: {len(location_coords)}/{len(locations)} locations resolved, "
                f"{updated} tender row(s) updated, {len(unresolved)} unresolved."
            )
        )

        if unresolved:
            with open("unresolved_locations.log", "a") as f:
                for entry in unresolved:
                    f.write(f"{entry}\n")
            self.stdout.write(self.style.WARNING("Unresolved entries appended to unresolved_locations.log"))
