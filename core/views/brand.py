"""Brand side: discover creators, run campaigns, read the results."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from core.models import COUNTRIES, Creator, Topic
from core.services import fit_score

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
    return render(request, "app/creator_detail.html", {"creator": creator})
