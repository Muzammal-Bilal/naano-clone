"""Public pages: the marketing site and the way in."""

from django.contrib.auth import login
from django.shortcuts import redirect, render

from core.forms import SignupForm
from core.models import Creator, compact
from core.services import fit_score

HOW_IT_WORKS = [
    {
        "title": "Find creators your buyers trust",
        "body": "Filter 3,000+ vetted B2B voices by topic, country, audience size and price, "
                "then compare them on audience fit rather than follower count.",
    },
    {
        "title": "Build a campaign brief in minutes",
        "body": "Set the objective and key messages once. Every creator you book works from "
                "the same brief, with the do's and don'ts spelled out.",
    },
    {
        "title": "Manage every collaboration",
        "body": "Track each post from invited to accepted, draft, scheduled and live, "
                "without chasing anyone over email.",
    },
    {
        "title": "Track reach, clicks, and leads",
        "body": "Every post carries a tracked link, so spend maps to a specific creator "
                "instead of an impression pool.",
    },
    {
        "title": "Pay creators without the admin",
        "body": "One wallet covers the campaign. Creators get paid on schedule and never "
                "have to raise an invoice.",
    },
]

def _stat(value, label, style="compact"):
    """A headline number the page counts up to.

    `display` is the finished string rendered server-side, so the figure is
    correct before Alpine loads and stays correct if it never does. It is
    derived from `value` rather than written out, which keeps the animated
    target and the static fallback from drifting apart.
    """
    display = compact(value) if style == "compact" else f"{value:,}"
    return {"value": value, "style": style, "display": f"{display}+", "label": label}


# Wordmarks for the social-proof marquee. Naano shows real customer logos; these
# are set as text because shipping other companies' trademarks into a clone is
# not a thing to do casually.
LOGOS = ["La Growth Machine", "gojiberry", "ChatSEO", "Abyssale", "BlogSEO", "lemlist", "folk."]

STATS = [
    _stat(5_000_000, "Impressions generated"),
    _stat(30_000, "Leads generated"),
    _stat(2_000, "Creators on Naano", style="comma"),
    _stat(5_000, "Posts published"),
]


def home(request):
    """Public front door. Must look right to a signed-out visitor."""
    creators = list(Creator.objects.prefetch_related("topics").order_by("-engagement_rate")[:6])
    for creator in creators:
        # No ICP for an anonymous visitor, so this is the creator's baseline fit.
        creator.preview_score = fit_score(creator, topic_ids=[], countries=[])

    return render(request, "public/home.html", {
        "creators": creators,
        "steps": HOW_IT_WORKS,
        "stats": STATS,
        "logos": LOGOS,
    })


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")

    return render(request, "auth/signup.html", {"form": form})
