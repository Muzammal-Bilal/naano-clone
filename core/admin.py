"""Admin registration.

Django's admin is free back-office for a demo: it lets a reviewer inspect the
data model directly without me building CRUD screens for every entity.
"""

from django.contrib import admin

from .models import Booking, Brand, Campaign, Creator, PostMetric, Topic, Transaction


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "headline", "country", "followers", "price_per_post", "verified")
    list_filter = ("verified", "country", "topics")
    search_fields = ("display_name", "headline", "bio")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("company_name", "industry", "wallet_balance")
    search_fields = ("company_name",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "objective", "status", "budget", "created_at")
    list_filter = ("status", "objective", "pricing_model")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("creator", "campaign", "status", "price", "scheduled_for")
    list_filter = ("status",)
    autocomplete_fields = ("creator",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "amount", "created_at")
    list_filter = ("kind",)


admin.site.register([Topic, PostMetric])
admin.site.site_header = "Naano admin"
