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

TESTIMONIAL = {
    "quote": "We manage \u20ac10M+ of influence budget every year. For B2B, Naano simply "
             "makes our life easier.",
    "name": "David Zmirov",
    "role": "CEO, Zmirov Communication",
    "company": "Influence agency",
}

# Static previews for the feature-card mockups. Hard-coded rather than queried:
# these illustrate what a screen looks like, so they should stay stable even when
# the seeded data changes underneath them.
FIT_PREVIEW = [("Eric", 92), ("Robin", 88), ("Aya", 84)]
PIPELINE_PREVIEW = [
    ("Raphael", "Draft ready", "bg-amber-100 text-amber-800"),
    ("Thomas", "Scheduled", "bg-sky-100 text-sky-800"),
    ("Nada", "Live", "bg-emerald-100 text-emerald-800"),
]
BAR_PREVIEW = [35, 52, 44, 68, 60, 82, 74, 100]

CASE_STUDY = {
    "brand": "BlogSEO",
    "quote": "Naano became one of our fastest acquisition channels. We know exactly what "
             "every creator brings.",
    "name": "Vincent Josse",
    "role": "CEO & Founder, BlogSEO",
    "title": "How BlogSEO turned creator content into product signups",
    "body": "BlogSEO briefed SEO and SaaS creators on LinkedIn, then traced every trial back "
            "to the post that drove it.",
    "metrics": [("9", "creators activated"), ("2,940", "qualified clicks"), ("512", "trials started")],
}

# Sample published posts. These make the attribution story concrete: a reviewer
# can see a post next to the numbers it produced without signing in first.
EXAMPLE_POSTS = [
    {
        "name": "Thomas Higad\u00e8re", "meta": "Creator \u00b7 B2B & AI \u00b7 34K followers",
        "text": "How AI changed our prospecting workflow for wealth managers and private bankers.",
        "impressions": "42.8K", "clicks": "312", "leads": "18", "brand": "Zmirov",
    },
    {
        "name": "Robin Tempe", "meta": "Creator \u00b7 Sales & AI \u00b7 12K followers",
        "text": "I run my entire prospecting workflow through an AI. Here is how.",
        "impressions": "9K", "clicks": "100", "leads": "50", "brand": "BlogSEO",
    },
    {
        "name": "Eric Djavid", "meta": "Sales Leader \u00b7 B2B \u00b7 40K followers",
        "text": "Most sales teams spend 80% of their time on the wrong leads. Here is how I changed that.",
        "impressions": "20K", "clicks": "350", "leads": "80", "brand": "lemlist",
    },
    {
        "name": "Marina Panova", "meta": "Content Creator \u00b7 B2B \u00b7 34K followers",
        "text": "How I build my 30-day LinkedIn content system, the exact playbook.",
        "impressions": "100K", "clicks": "1,600", "leads": "320", "brand": "folk.",
    },
]

# Pricing is presented, not transacted. The plans are real and the copy is
# honest about what each includes; what is missing is a checkout, which is a
# payments integration rather than a product decision.
PLANS = [
    {
        "badge": "SELF-SERVE",
        "name": "Run it yourself.",
        "blurb": "For teams that want the infrastructure to run creator campaigns in-house.",
        "price": "\u20ac0",
        "period": "/ month",
        "cta": "Start for free",
        "featured": False,
        "features": [
            "Creator marketplace access",
            "Brief creation from your objective",
            "Track clicks, companies and pipeline",
            "Automatic creator payouts",
        ],
    },
    {
        "badge": "MANAGED CAMPAIGNS",
        "name": "Get your time back.",
        "blurb": "For teams that want Naano to operate their creator channel end to end.",
        "price": "Custom quote",
        "period": "",
        "cta": "Book a campaign call",
        "featured": True,
        "features": [
            "Campaign strategy and positioning",
            "Creator sourcing and coordination",
            "Brief creation and campaign launch",
            "Reporting and optimisation",
        ],
    },
]

FAQS = [
    ("What is Naano?",
     "A B2B LinkedIn creator marketplace. Companies discover and book vetted creators "
     "for sponsored posts, each at a fixed price per post set by the creator. Audiences "
     "run from niche voices around 1,000 followers to established creators with several "
     "hundred thousand."),
    ("How does Naano find the right creators?",
     "Every creator is scored against your ICP: the topics you sell into, the countries "
     "your buyers are in, and your budget. Results are ranked by that fit rather than by "
     "follower count, because a 2,000-follower voice speaking to your exact buyer beats a "
     "200,000-follower generalist."),
    ("Which networks do you support?",
     "LinkedIn, which is where B2B buying conversations actually happen. X is the obvious "
     "next one and the data model already allows for it."),
    ("How does per-post pricing work?",
     "Creators set their own price per post. You see it before you book, next to the cost "
     "per view it implies, so two creators can be compared on the same terms."),
    ("How does attribution work?",
     "Every post carries a tracked link, so clicks, leads and pipeline map back to the "
     "creator and campaign that produced them instead of to an anonymous impression pool."),
    ("Do you handle creator payouts?",
     "Yes. One wallet funds the campaign, creators are paid on schedule, and nobody has to "
     "raise an invoice."),
    ("What's the difference between Free and Done for you?",
     "Free gives you the platform and you run campaigns yourself. Done for you means the "
     "strategy, sourcing, briefing and reporting are handled for you."),
    ("Can I upgrade or cancel anytime?",
     "Yes. Campaign spend is separate, there is no lock-in, and you can cancel at any time."),
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
        "testimonial": TESTIMONIAL,
        "fit_preview": FIT_PREVIEW,
        "pipeline_preview": PIPELINE_PREVIEW,
        "bar_preview": BAR_PREVIEW,
        "case_study": CASE_STUDY,
        "posts": EXAMPLE_POSTS,
        "plans": PLANS,
        "faqs": FAQS,
    })


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")

    return render(request, "auth/signup.html", {"form": form})
