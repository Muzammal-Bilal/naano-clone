"""Populate the database with a believable marketplace.

Idempotent and deterministic: it clears its own data and reseeds from a fixed
random seed, so every deploy produces the same demo and the live link is never
an empty shell.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from core.models import Booking, Brand, Campaign, Creator, PostMetric, Topic, Transaction
from core.services import generate_brief

TOPICS = [
    "AI / SaaS", "Growth / GTM", "Sales / Prospecting", "Marketing / Content",
    "Product / Design", "Engineering", "Fintech", "HR / Recruiting",
    "Data / Analytics", "Cybersecurity", "Agencies / Consulting", "Founder / Startups",
]

COUNTRIES = ["FR", "DE", "GB", "NL", "ES", "IT", "BE", "SE", "US", "IE", "PL", "CA"]

DEMO_PASSWORD = "demo1234"

FIRST = [
    "Aymane", "Emma", "Augustin", "Raghav", "Daniel", "Pierre", "Marina", "Thomas",
    "Robin", "Eric", "Nada", "Sofia", "Lucas", "Chloe", "Mateo", "Ines", "Felix",
    "Amara", "Jonas", "Camille", "Nikhil", "Laura", "Viktor", "Yasmin", "Hugo",
    "Elena", "Omar", "Greta", "Sander", "Priya", "Tomas", "Aisha", "Noah", "Clara",
]
LAST = [
    "Junior", "Guetta", "Rudigoz", "Jerath", "Meisen", "Davadan", "Panova", "Higadere",
    "Tempe", "Djavid", "Bensaid", "Moreau", "Lindqvist", "Okafor", "Rossi", "Vasquez",
    "Novak", "Kaur", "Bauer", "Dubois", "Castellanos", "Andersen", "Mwangi", "Fischer",
]

HEADLINES = [
    "AI - SaaS", "AI - Media / Content", "Productivity - Fintech",
    "Growth / GTM - Software", "Growth / GTM - Agencies / Consulting", "SaaS - AI",
    "Sales Leader - B2B", "Content Creator - B2B", "Data - Analytics",
    "Security - Enterprise", "Product - Design Systems", "Founder - Early stage",
]

BIOS = [
    "Building intelligent systems that turn data into impact. Turning complex problems into smart, scalable products.",
    "Entrepreneurs, operateurs investisseurs. Reprise de PME francaises aux cotes de leur equipe.",
    "International Business School graduate, experience working at a YC company.",
    "I write about the unglamorous parts of go-to-market that actually move revenue.",
    "Ex-agency, now in-house. Sharing what works and what quietly does not.",
    "Fifteen years in enterprise sales. Mostly posting about what I got wrong.",
    "Helping technical founders explain their product without the jargon.",
    "Weekly breakdowns of B2B funnels, with the numbers left in.",
]

CAMPAIGNS = [
    ("Q3 pipeline push", "pipeline", "Attribution that survives a CFO review."),
    ("Product launch: Canvas", "signups", "A collaborative workspace for GTM teams."),
    ("Category education", "awareness", "Why creator-led beats paid social in B2B."),
    ("Engineering brand", "hiring", "How our platform team ships on Fridays."),
]


class Command(BaseCommand):
    help = "Reset and reseed the demo marketplace."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Seed only when there is no data. Used on boot so a redeploy "
                 "does not wipe accounts a reviewer created.",
        )

    def handle(self, *args, **options):
        if options["if_empty"] and Creator.objects.exists():
            self.stdout.write("Data already present, skipping seed.")
            return

        random.seed(8)

        with transaction.atomic():
            self._clear()
            topics = self._topics()
            creators = self._creators(topics)
            brand = self._brand(topics)
            self._campaigns(brand, creators)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(creators)} creators, {Campaign.objects.count()} campaigns, "
            f"{Booking.objects.count()} bookings, {PostMetric.objects.count()} metric rows."
        ))

    def _clear(self):
        Transaction.objects.all().delete()
        PostMetric.objects.all().delete()
        Booking.objects.all().delete()
        Campaign.objects.all().delete()
        Creator.objects.all().delete()
        Brand.objects.all().delete()
        Topic.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _topics(self):
        return [
            Topic.objects.create(name=name, slug=slugify(name))
            for name in TOPICS
        ]

    def _creators(self, topics):
        # Hash the shared demo password once. Doing it per user turned seeding
        # into a three-minute job, which a deploy release command will not wait for.
        password = make_password(DEMO_PASSWORD)
        creators = []
        used = set()

        for index in range(80):
            while True:
                name = f"{random.choice(FIRST)} {random.choice(LAST)}"
                if name not in used:
                    used.add(name)
                    break

            handle = slugify(name)
            user = User.objects.create(
                username=handle,
                email=f"{handle}@creators.naano.demo",
                password=password,
                first_name=name.split()[0],
                last_name=name.split()[1],
            )

            # Price tracks audience size with noise, so cost-per-view stays plausible.
            followers = random.choice([
                random.randint(1_200, 9_000),
                random.randint(9_000, 40_000),
                random.randint(40_000, 180_000),
            ])
            median_views = int(followers * random.uniform(0.35, 1.4))
            price = Decimal(str(round(max(20, followers * random.uniform(0.004, 0.011)), -1)))

            gender = random.choice(["men", "women"])
            creator = Creator.objects.create(
                user=user,
                display_name=name,
                headline=random.choice(HEADLINES),
                bio=random.choice(BIOS),
                avatar_url=f"https://randomuser.me/api/portraits/{gender}/{index % 99}.jpg",
                country=random.choice(COUNTRIES),
                followers=followers,
                median_views=median_views,
                engagement_rate=Decimal(str(round(random.uniform(1.4, 6.5), 2))),
                price_per_post=price,
                verified=random.random() > 0.25,
            )
            creator.topics.set(random.sample(topics, random.randint(1, 3)))
            creators.append(creator)

        # A known login so a reviewer can see the creator side without signing up.
        demo = creators[0]
        demo.user.username = "creator"
        demo.user.email = "creator@demo.naano"
        demo.user.save(update_fields=["username", "email"])

        return creators

    def _brand(self, topics):
        user = User.objects.create(
            username="brand",
            email="brand@demo.naano",
            password=make_password(DEMO_PASSWORD),
            first_name="Vincent",
            last_name="Josse",
        )
        brand = Brand.objects.create(
            user=user,
            company_name="BlogSEO",
            industry="SEO and content software",
            website="https://blogseo.example",
            icp_countries="FR,DE,GB,NL",
            wallet_balance=Decimal("12500.00"),
        )
        brand.icp_topics.set(topics[:4])
        Transaction.objects.create(
            user=user, kind=Transaction.Kind.TOPUP,
            amount=Decimal("12500.00"), note="Initial wallet top-up",
        )
        return brand

    def _campaigns(self, brand, creators):
        today = date.today()

        for offset, (name, objective, description) in enumerate(CAMPAIGNS):
            brief = generate_brief(brand.company_name, objective, description)
            campaign = Campaign.objects.create(
                brand=brand,
                name=name,
                objective=objective,
                product_description=description,
                budget=Decimal(str(random.choice([2500, 4000, 6000, 9000]))),
                landing_url="https://blogseo.example/trial",
                starts_at=today - timedelta(days=30 - offset * 7),
                status=Campaign.Status.ACTIVE if offset < 3 else Campaign.Status.DRAFT,
                **brief,
            )

            for creator in random.sample(creators, random.randint(3, 6)):
                status = random.choice(Booking.PIPELINE)
                booking = Booking.objects.create(
                    campaign=campaign,
                    creator=creator,
                    price=creator.price_per_post,
                    status=status,
                    scheduled_for=today + timedelta(days=random.randint(-20, 10)),
                    draft_content=(
                        "Most teams treat this as a tooling problem. It is a process "
                        "problem, and here is the version that finally worked for us."
                        if status not in (Booking.Status.INVITED, Booking.Status.ACCEPTED) else ""
                    ),
                )
                if status in (Booking.Status.LIVE, Booking.Status.COMPLETED):
                    self._metrics(booking, today)

    def _metrics(self, booking, today):
        """A decaying impression curve, the way a real post behaves after publishing."""
        live_days = random.randint(8, 28)
        peak = int(booking.creator.median_views * random.uniform(0.25, 0.6))
        total_pipeline = Decimal("0")

        for day in range(live_days):
            published = today - timedelta(days=live_days - day)
            decay = 0.55 ** day
            impressions = max(12, int(peak * decay * random.uniform(0.75, 1.25)))
            clicks = int(impressions * random.uniform(0.02, 0.09))
            leads = int(clicks * random.uniform(0.05, 0.22))
            pipeline = Decimal(str(leads * random.randint(180, 900)))
            total_pipeline += pipeline

            PostMetric.objects.create(
                booking=booking,
                date=published,
                impressions=impressions,
                clicks=clicks,
                leads=leads,
                likes=int(impressions * random.uniform(0.01, 0.04)),
                comments=int(impressions * random.uniform(0.001, 0.006)),
                pipeline_value=pipeline,
            )

        booking.post_url = "https://www.linkedin.com/posts/demo-post"
        booking.save(update_fields=["post_url"])

        Transaction.objects.create(
            user=booking.creator.user, kind=Transaction.Kind.PAYOUT,
            amount=booking.price, booking=booking,
            note=f"Payout for {booking.campaign.name}",
        )
