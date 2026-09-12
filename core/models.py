"""Domain model for the naano clone.

Two sides of one marketplace. A user is a Creator or a Brand depending on which
profile row points at them, so there is no separate role column that can drift
out of sync with reality.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


COUNTRIES = {
    "FR": "France", "DE": "Germany", "GB": "United Kingdom", "NL": "Netherlands",
    "ES": "Spain", "IT": "Italy", "BE": "Belgium", "SE": "Sweden",
    "US": "United States", "CA": "Canada", "IE": "Ireland", "PL": "Poland",
}


def flag(country_code):
    """ISO-3166 alpha-2 to its regional-indicator emoji. Beats shipping a flag sprite."""
    code = (country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in code)


def compact(number):
    """12400 -> 12.4K, matching how naano prints audience numbers."""
    number = number or 0
    if number < 1000:
        return str(number)
    if number < 1_000_000:
        trimmed = f"{number / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{trimmed}K"
    trimmed = f"{number / 1_000_000:.1f}".rstrip("0").rstrip(".")
    return f"{trimmed}M"


class Topic(models.Model):
    """A B2B niche such as Growth / GTM or AI / SaaS."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Creator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="creator")
    display_name = models.CharField(max_length=80)
    headline = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    country = models.CharField(max_length=2, default="FR")
    topics = models.ManyToManyField(Topic, related_name="creators")

    followers = models.PositiveIntegerField(default=0)
    median_views = models.PositiveIntegerField(default=0)
    engagement_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    price_per_post = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-followers"]

    def __str__(self):
        return self.display_name

    @property
    def flag(self):
        return flag(self.country)

    @property
    def country_name(self):
        return COUNTRIES.get(self.country.upper(), self.country.upper())

    @property
    def followers_display(self):
        return compact(self.followers)

    @property
    def views_display(self):
        return compact(self.median_views)

    @property
    def cost_per_view(self):
        if not self.median_views:
            return Decimal("0")
        return (self.price_per_post / self.median_views).quantize(Decimal("0.01"))


class Brand(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="brand")
    company_name = models.CharField(max_length=80)
    industry = models.CharField(max_length=80, blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)

    # Ideal customer profile, used to score creator fit.
    icp_topics = models.ManyToManyField(Topic, related_name="brands", blank=True)
    icp_countries = models.CharField(
        max_length=120, blank=True, help_text="Comma-separated ISO country codes."
    )
    wallet_balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )

    def __str__(self):
        return self.company_name

    @property
    def target_countries(self):
        return [c.strip().upper() for c in self.icp_countries.split(",") if c.strip()]


class Campaign(models.Model):
    class Objective(models.TextChoices):
        AWARENESS = "awareness", "Brand awareness"
        PIPELINE = "pipeline", "Pipeline and leads"
        SIGNUPS = "signups", "Product signups"
        HIRING = "hiring", "Employer brand"

    class Pricing(models.TextChoices):
        FLAT = "flat", "Flat fee per post"
        CPC = "cpc", "Cost per qualified click"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=120)
    objective = models.CharField(
        max_length=20, choices=Objective.choices, default=Objective.PIPELINE
    )
    pricing_model = models.CharField(
        max_length=10, choices=Pricing.choices, default=Pricing.FLAT
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    product_description = models.TextField(blank=True)
    key_messages = models.TextField(blank=True)
    guidelines = models.TextField(blank=True)
    dos = models.TextField(blank=True)
    donts = models.TextField(blank=True)

    budget = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    landing_url = models.URLField(blank=True)
    starts_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def committed_spend(self):
        return sum((b.price for b in self.bookings.all()), Decimal("0"))


class Booking(models.Model):
    """One creator's participation in one campaign, and its lifecycle."""

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        DRAFT = "draft", "Draft ready"
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        COMPLETED = "completed", "Completed"

    # Stages that represent forward progress, in pipeline order.
    PIPELINE = [
        Status.INVITED,
        Status.ACCEPTED,
        Status.DRAFT,
        Status.SCHEDULED,
        Status.LIVE,
        Status.COMPLETED,
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="bookings")
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="bookings")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.INVITED)

    draft_content = models.TextField(blank=True)
    scheduled_for = models.DateField(null=True, blank=True)
    post_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "creator"], name="unique_creator_per_campaign"
            )
        ]

    def __str__(self):
        return f"{self.creator.display_name} on {self.campaign.name}"

    @property
    def is_open(self):
        return self.status not in (self.Status.DECLINED, self.Status.COMPLETED)

    def totals(self):
        """Aggregate this booking's daily metrics."""
        return self.metrics.aggregate(
            impressions=models.Sum("impressions"),
            clicks=models.Sum("clicks"),
            leads=models.Sum("leads"),
            pipeline=models.Sum("pipeline_value"),
        )


class PostMetric(models.Model):
    """One day of performance for one booked post."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="metrics")
    date = models.DateField()
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    leads = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    pipeline_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "date"], name="unique_metric_per_booking_day"
            )
        ]


class Transaction(models.Model):
    """Wallet ledger. Records money movement without moving any."""

    class Kind(models.TextChoices):
        TOPUP = "topup", "Wallet top-up"
        CHARGE = "charge", "Campaign charge"
        PAYOUT = "payout", "Creator payout"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    booking = models.ForeignKey(
        Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    note = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
