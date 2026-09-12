"""Brand side: discover creators, run campaigns, read the results."""

from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import CampaignForm
from core.models import COUNTRIES, Booking, Campaign, Creator, PostMetric, Topic
from core.services import fit_score, generate_brief

SORTS = {
    "fit": "Best fit",
    "followers": "Largest audience",
    "price_low": "Lowest price",
    "price_high": "Highest price",
    "engagement": "Most engaged",
}


def brand_required(view):
    """Brand-only pages. Creators get a 404 rather than a redirect loop."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        brand = getattr(request.user, "brand", None)
        if brand is None:
            raise Http404("This page is for brand accounts.")
        return view(request, brand, *args, **kwargs)
    return wrapper


def _filtered(request, brand):
    """Apply the discover filters, score the survivors, sort, and return them.

    Scoring happens in Python rather than SQL because fit weighs topic overlap
    against the brand's ICP, which is a set operation the ORM cannot express
    cheaply. The filters run in the database first so only a narrowed set is
    ever scored.
    """
    params = request.GET
    creators = Creator.objects.prefetch_related("topics")

    query = params.get("q", "").strip()
    if query:
        creators = creators.filter(
            Q(display_name__icontains=query)
            | Q(headline__icontains=query)
            | Q(bio__icontains=query)
        )

    topic_ids = [int(t) for t in params.getlist("topic") if t.isdigit()]
    if topic_ids:
        creators = creators.filter(topics__id__in=topic_ids).distinct()

    countries = [c for c in params.getlist("country") if c in COUNTRIES]
    if countries:
        creators = creators.filter(country__in=countries)

    if (max_price := params.get("max_price", "")).isdigit():
        creators = creators.filter(price_per_post__lte=int(max_price))
    if (min_followers := params.get("min_followers", "")).isdigit():
        creators = creators.filter(followers__gte=int(min_followers))

    # Fall back to the brand's saved ICP so the first page is already relevant.
    score_topics = topic_ids or list(brand.icp_topics.values_list("id", flat=True))
    score_countries = countries or brand.target_countries

    scored = list(creators)
    for creator in scored:
        creator.score = fit_score(creator, score_topics, score_countries)

    sort = params.get("sort", "fit")
    keys = {
        "fit": lambda c: -c.score,
        "followers": lambda c: -c.followers,
        "price_low": lambda c: c.price_per_post,
        "price_high": lambda c: -c.price_per_post,
        "engagement": lambda c: -c.engagement_rate,
    }
    scored.sort(key=keys.get(sort, keys["fit"]))
    return scored


@brand_required
def discover(request, brand):
    scored = _filtered(request, brand)
    page = Paginator(scored, 12).get_page(request.GET.get("page"))

    context = {
        "page_obj": page,
        "total": len(scored),
        "topics": Topic.objects.all(),
        "countries": sorted(COUNTRIES.items(), key=lambda item: item[1]),
        "sorts": SORTS,
        "selected_topics": [int(t) for t in request.GET.getlist("topic") if t.isdigit()],
        "selected_countries": request.GET.getlist("country"),
        "params": request.GET,
        "nav": "discover",
    }

    # HTMX swaps just the results, so filtering never reloads the page.
    if request.headers.get("HX-Request"):
        return render(request, "partials/creator_results.html", context)
    return render(request, "app/discover.html", context)


@brand_required
def creator_detail(request, brand, pk):
    creator = get_object_or_404(Creator.objects.prefetch_related("topics"), pk=pk)
    creator.score = fit_score(
        creator,
        list(brand.icp_topics.values_list("id", flat=True)),
        brand.target_countries,
    )

    if request.method == "POST":
        campaign = get_object_or_404(
            Campaign, pk=request.POST.get("campaign"), brand=brand
        )
        booking, created = Booking.objects.get_or_create(
            campaign=campaign, creator=creator,
            defaults={"price": creator.price_per_post},
        )
        if created:
            messages.success(
                request, f"{creator.display_name} invited to {campaign.name}."
            )
        else:
            messages.info(request, f"Already booked on {campaign.name}.")
        return redirect("campaign_detail", pk=campaign.pk)

    return render(request, "app/creator_detail.html", {
        "creator": creator,
        "campaigns": brand.campaigns.exclude(status=Campaign.Status.COMPLETED),
        "booked_on": set(
            Booking.objects.filter(creator=creator, campaign__brand=brand)
            .values_list("campaign_id", flat=True)
        ),
    })


@brand_required
def campaigns(request, brand):
    return render(request, "app/campaigns.html", {
        "campaigns": brand.campaigns.prefetch_related("bookings__creator"),
        "nav": "campaigns",
    })


@brand_required
def campaign_new(request, brand):
    form = CampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save(commit=False)
        campaign.brand = brand
        # Draft the brief copy from the structured inputs the brand just gave us.
        for field, value in generate_brief(
            brand.company_name, campaign.objective, campaign.product_description
        ).items():
            setattr(campaign, field, value)
        campaign.save()
        messages.success(request, "Campaign created. Now add creators to it.")
        return redirect("campaign_detail", pk=campaign.pk)

    return render(request, "app/campaign_new.html", {"form": form, "nav": "campaigns"})


@brand_required
def campaign_detail(request, brand, pk):
    campaign = get_object_or_404(
        Campaign.objects.prefetch_related("bookings__creator", "bookings__metrics"),
        pk=pk, brand=brand,
    )

    if request.method == "POST":
        booking = get_object_or_404(
            Booking, pk=request.POST.get("booking"), campaign=campaign
        )
        target = request.POST.get("status")
        if target in Booking.Status.values:
            booking.status = target
            booking.save(update_fields=["status"])
            messages.success(
                request,
                f"{booking.creator.display_name} moved to {booking.get_status_display()}.",
            )
        return redirect("campaign_detail", pk=campaign.pk)

    bookings = list(campaign.bookings.all())
    return render(request, "app/campaign_detail.html", {
        "campaign": campaign,
        "columns": [
            (status, status.label, [b for b in bookings if b.status == status])
            for status in Booking.PIPELINE
        ],
        "declined": [b for b in bookings if b.status == Booking.Status.DECLINED],
        "totals": _rollup(bookings),
        "nav": "campaigns",
    })


def _rollup(bookings):
    """Sum daily metrics across a set of bookings."""
    totals = {"impressions": 0, "clicks": 0, "leads": 0, "pipeline": Decimal("0")}
    for booking in bookings:
        for metric in booking.metrics.all():
            totals["impressions"] += metric.impressions
            totals["clicks"] += metric.clicks
            totals["leads"] += metric.leads
            totals["pipeline"] += metric.pipeline_value
    return totals


@brand_required
def analytics(request, brand):
    metrics = (
        PostMetric.objects
        .filter(booking__campaign__brand=brand)
        .values("date")
        .annotate(
            impressions=Sum("impressions"),
            clicks=Sum("clicks"),
            leads=Sum("leads"),
            pipeline=Sum("pipeline_value"),
        )
        .order_by("date")
    )
    series = list(metrics)

    per_campaign = (
        Campaign.objects
        .filter(brand=brand)
        .annotate(
            impressions=Sum("bookings__metrics__impressions"),
            clicks=Sum("bookings__metrics__clicks"),
            leads=Sum("bookings__metrics__leads"),
            pipeline=Sum("bookings__metrics__pipeline_value"),
            spend=Sum("bookings__price", distinct=True),
        )
        .order_by("-pipeline")
    )

    totals = {
        "impressions": sum(row["impressions"] for row in series),
        "clicks": sum(row["clicks"] for row in series),
        "leads": sum(row["leads"] for row in series),
        "pipeline": sum((row["pipeline"] for row in series), Decimal("0")),
    }
    totals["ctr"] = (
        round(totals["clicks"] / totals["impressions"] * 100, 2)
        if totals["impressions"] else 0
    )

    return render(request, "app/analytics.html", {
        "totals": totals,
        "campaigns": per_campaign,
        # Passed as a dict, not a JSON string: json_script serialises it, and
        # double-encoding would hand the page a string where it expects an object.
        "chart": {
            "labels": [row["date"].strftime("%d %b") for row in series],
            "impressions": [row["impressions"] for row in series],
            "clicks": [row["clicks"] for row in series],
            "leads": [row["leads"] for row in series],
        },
        "nav": "analytics",
    })
