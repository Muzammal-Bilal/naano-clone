"""Views for the naano clone.

Server-rendered. HTMX swaps partials for the marketplace filters rather than
running a separate client app.
"""

from django.shortcuts import render

from .models import Creator
from .services import fit_score

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

STATS = [
    {"value": "5M+", "label": "Impressions generated"},
    {"value": "30K+", "label": "Leads generated"},
    {"value": "2,000+", "label": "Creators on Naano"},
    {"value": "5K+", "label": "Posts published"},
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
    })
