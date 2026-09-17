from django.contrib import admin

from .models import Company, Lot, Tender, Verdict


class LotInline(admin.TabularInline):
    model = Lot
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "region_center", "region_radius_km", "contract_min", "contract_max")
    search_fields = ("name",)


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ("title", "external_id", "location", "contract_value", "extracted_at")
    search_fields = ("title", "external_id")
    inlines = [LotInline]


@admin.register(Verdict)
class VerdictAdmin(admin.ModelAdmin):
    list_display = ("company", "tender", "lot", "verdict", "reason_code", "evaluated_at")
    list_filter = ("verdict", "reason_code", "company")
