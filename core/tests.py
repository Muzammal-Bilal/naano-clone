"""QA suite.

Focused on the things that would actually hurt: one account reading or writing
another account's data, and the booking lifecycle accepting transitions it
should refuse. Presentation is not tested here; a broken layout is visible, a
broken permission is not.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Booking, Brand, Campaign, Creator, Topic

PASSWORD = "qa-pass-1234"

BRAND_PAGES = ["discover", "campaigns", "campaign_new", "analytics"]
CREATOR_PAGES = ["creator_deals", "creator_earnings"]


def make_brand(username, company):
    user = User.objects.create_user(username=username, password=PASSWORD)
    return Brand.objects.create(user=user, company_name=company)


def make_creator(username, name, price="200"):
    user = User.objects.create_user(username=username, password=PASSWORD)
    return Creator.objects.create(
        user=user, display_name=name, headline="B2B voice",
        followers=10_000, median_views=8_000,
        engagement_rate=Decimal("4.0"), price_per_post=Decimal(price),
    )


class Fixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic = Topic.objects.create(name="Growth / GTM", slug="growth-gtm")
        cls.brand = make_brand("brand-one", "Acme")
        cls.other_brand = make_brand("brand-two", "Rival")
        cls.creator = make_creator("creator-one", "Ada Voice")
        cls.other_creator = make_creator("creator-two", "Bo Voice")

        cls.campaign = Campaign.objects.create(brand=cls.brand, name="Q1 launch")
        cls.other_campaign = Campaign.objects.create(brand=cls.other_brand, name="Rival push")
        cls.booking = Booking.objects.create(
            campaign=cls.campaign, creator=cls.creator, price=Decimal("200"),
        )

    def as_brand(self):
        self.client.login(username="brand-one", password=PASSWORD)

    def as_other_brand(self):
        self.client.login(username="brand-two", password=PASSWORD)

    def as_creator(self):
        self.client.login(username="creator-one", password=PASSWORD)

    def as_other_creator(self):
        self.client.login(username="creator-two", password=PASSWORD)


class PublicPages(Fixtures):
    def test_every_public_page_renders_signed_out(self):
        for name in ["home", "creators_page", "agencies_page", "blog",
                     "tools", "case_study", "login", "signup"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_unknown_url_returns_404(self):
        self.assertEqual(self.client.get("/no-such-page/").status_code, 404)


class AccessControl(Fixtures):
    def test_anonymous_is_sent_to_login(self):
        for name in BRAND_PAGES + CREATOR_PAGES:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response["Location"])

    def test_creator_cannot_open_brand_pages(self):
        self.as_creator()
        for name in BRAND_PAGES:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 404)

    def test_brand_cannot_open_creator_pages(self):
        self.as_brand()
        for name in CREATOR_PAGES:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 404)


class ObjectOwnership(Fixtures):
    def test_brand_cannot_read_another_brands_campaign(self):
        self.as_brand()
        url = reverse("campaign_detail", args=[self.other_campaign.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_creator_cannot_read_another_creators_deal(self):
        self.as_other_creator()
        url = reverse("creator_deal_detail", args=[self.booking.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_brand_cannot_book_onto_another_brands_campaign(self):
        self.as_brand()
        url = reverse("creator_detail", args=[self.other_creator.pk])
        response = self.client.post(url, {"campaign": self.other_campaign.pk})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            Booking.objects.filter(campaign=self.other_campaign).exists()
        )

    def test_brand_cannot_move_another_brands_booking(self):
        self.as_other_brand()
        url = reverse("campaign_detail", args=[self.other_campaign.pk])
        self.client.post(url, {"booking": self.booking.pk, "status": "live"})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.INVITED)


class Pipeline(Fixtures):
    def test_booking_a_creator_twice_does_not_duplicate(self):
        self.as_brand()
        url = reverse("creator_detail", args=[self.creator.pk])
        self.client.post(url, {"campaign": self.campaign.pk})
        self.assertEqual(
            Booking.objects.filter(campaign=self.campaign, creator=self.creator).count(), 1
        )

    def test_unknown_status_value_is_ignored(self):
        self.as_brand()
        url = reverse("campaign_detail", args=[self.campaign.pk])
        self.client.post(url, {"booking": self.booking.pk, "status": "deleted"})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.INVITED)

    def test_creator_can_accept_an_invitation(self):
        self.as_creator()
        url = reverse("creator_deal_detail", args=[self.booking.pk])
        self.client.post(url, {"action": "accept"})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.ACCEPTED)

    def test_accept_does_nothing_once_declined(self):
        self.booking.status = Booking.Status.DECLINED
        self.booking.save()
        self.as_creator()
        url = reverse("creator_deal_detail", args=[self.booking.pk])
        self.client.post(url, {"action": "accept"})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.DECLINED)

    def test_declined_deal_cannot_be_revived_with_a_draft(self):
        self.booking.status = Booking.Status.DECLINED
        self.booking.save()
        self.as_creator()
        url = reverse("creator_deal_detail", args=[self.booking.pk])
        self.client.post(url, {"action": "submit_draft", "draft_content": "sneaky"})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.DECLINED)

    def test_empty_draft_is_rejected(self):
        self.booking.status = Booking.Status.ACCEPTED
        self.booking.save()
        self.as_creator()
        url = reverse("creator_deal_detail", args=[self.booking.pk])
        self.client.post(url, {"action": "submit_draft", "draft_content": "   "})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.ACCEPTED)


class Signup(Fixtures):
    """The first thing a reviewer touches, so it gets its own coverage."""

    def post(self, **overrides):
        data = {"role": "brand", "full_name": "Sam New",
                "email": "sam@example.com", "password": "long-enough-1",
                "context": "Newco"}
        data.update(overrides)
        return self.client.post(reverse("signup"), data)

    def test_brand_signup_creates_a_brand_and_lands_in_the_app(self):
        self.assertRedirects(self.post(), reverse("dashboard"), target_status_code=302)
        user = User.objects.get(email="sam@example.com")
        self.assertTrue(hasattr(user, "brand"))
        self.assertFalse(hasattr(user, "creator"))

    def test_creator_signup_creates_a_creator(self):
        self.post(role="creator", email="cre@example.com")
        user = User.objects.get(email="cre@example.com")
        self.assertTrue(hasattr(user, "creator"))
        self.assertFalse(hasattr(user, "brand"))

    def test_duplicate_email_is_rejected(self):
        self.post()
        # Signing up logs you straight in, and the view bounces authenticated
        # users to the dashboard, so sign out before trying the email again.
        self.client.logout()
        response = self.post(full_name="Copy Cat")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.filter(email="sam@example.com").count(), 1)

    def test_short_password_is_rejected(self):
        response = self.post(password="short")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="sam@example.com").exists())

    def test_dashboard_routes_each_role_to_its_own_home(self):
        self.as_brand()
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("discover"))
        self.client.logout()
        self.as_creator()
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("creator_deals"))


class Discover(Fixtures):
    def test_htmx_request_returns_only_the_results(self):
        self.as_brand()
        url = reverse("discover")
        full = self.client.get(url)
        partial = self.client.get(url, headers={"HX-Request": "true"})
        self.assertContains(full, "<html")
        self.assertNotContains(partial, "<html")

    def test_price_filter_excludes_dearer_creators(self):
        make_creator("creator-rich", "Costly", price="5000")
        self.as_brand()
        response = self.client.get(reverse("discover"), {"max_price": "300"})
        self.assertNotContains(response, "Costly")
        self.assertContains(response, "Ada Voice")
