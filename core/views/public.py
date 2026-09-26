"""Public pages: the marketing site and the way in."""

from django.contrib.auth import login
from django.db.models import Sum
from django.shortcuts import redirect, render

from core.forms import SignupForm
from core.models import Booking, Creator, PostMetric, compact

HOW_IT_WORKS = [
    {
        "title": "Find creators your buyers trust",
        "body": "Filter vetted B2B voices by topic, country, audience size and price, "
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
    "quote": "We run seven-figure influence budgets. For B2B, Campfire is the first "
             "tool that made creator ROI as clear as paid social.",
    "name": "Amira Soltani",
    "role": "Head of Growth",
    "company": "Northline Software",
}

FIT_PREVIEW = [("Eric", 92), ("Robin", 88), ("Aya", 84)]
PIPELINE_PREVIEW = [
    ("Raphael", "Draft ready", "bg-amber-100 text-amber-800"),
    ("Thomas", "Scheduled", "bg-ember/15 text-ember-deep"),
    ("Nada", "Live", "bg-emerald-100 text-emerald-800"),
]
BAR_PREVIEW = [35, 52, 44, 68, 60, 82, 74, 100]

CASE_STUDY = {
    "brand": "Atlas CRM",
    "quote": "Campfire became one of our fastest acquisition channels. We know exactly what "
             "every creator brings.",
    "name": "Jordan Hale",
    "role": "CEO & Founder, Atlas CRM",
    "title": "How Atlas CRM turned creator content into product signups",
    "body": "Atlas briefed SaaS creators on LinkedIn, then traced every trial back "
            "to the post that drove it — all inside Campfire.",
    "metrics": [("9", "creators activated"), ("2,940", "qualified clicks"), ("512", "trials started")],
}

EXAMPLE_POSTS = [
    {
        "name": "Thomas Higadère", "meta": "Creator · B2B & AI · 34K followers",
        "text": "How AI changed our prospecting workflow for wealth managers and private bankers.",
        "impressions": "42.8K", "clicks": "312", "leads": "18", "brand": "Northline",
    },
    {
        "name": "Robin Tempe", "meta": "Creator · Sales & AI · 12K followers",
        "text": "I run my entire prospecting workflow through an AI. Here is how.",
        "impressions": "9K", "clicks": "100", "leads": "50", "brand": "Atlas CRM",
    },
    {
        "name": "Eric Djavid", "meta": "Sales Leader · B2B · 40K followers",
        "text": "Most sales teams spend 80% of their time on the wrong leads. Here is how I changed that.",
        "impressions": "20K", "clicks": "350", "leads": "80", "brand": "Relay",
    },
    {
        "name": "Marina Panova", "meta": "Content Creator · B2B · 34K followers",
        "text": "How I build my 30-day LinkedIn content system, the exact playbook.",
        "impressions": "100K", "clicks": "1,600", "leads": "320", "brand": "Harbor",
    },
]

PLANS = [
    {
        "badge": "SELF-SERVE",
        "name": "Run it yourself.",
        "blurb": "For teams that want the infrastructure to run creator campaigns in-house.",
        "price": "€0",
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
        "blurb": "For teams that want Campfire to operate their creator channel end to end.",
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
    ("What is Campfire?",
     "A B2B LinkedIn creator marketplace. Companies discover and book vetted creators "
     "for sponsored posts, each at a fixed price per post set by the creator. Audiences "
     "run from niche voices around 1,000 followers to established creators with several "
     "hundred thousand."),
    ("How does Campfire find the right creators?",
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


def _stat(value, label, style="compact", suffix=""):
    """A headline number the page counts up to."""
    display = compact(value) if style == "compact" else f"{value:,}"
    return {
        "value": value,
        "style": style,
        "display": f"{display}{suffix}",
        "label": label,
    }


LOGOS = [
    ("Northline", False), ("Atlas CRM", True), ("Relay", False),
    ("Harbor", False), ("Kinetic", True), ("Parcel", False), ("Lumen", False),
]

AUDIENCE = [("AI & SaaS creator", "96%"), ("Founders", ""), ("Sales leaders", ""), ("GTM teams", "")]


def _live_stats():
    """Headline figures from the database — not inflated marketing fiction."""
    from django.db.models import Count

    creators = Creator.objects.count()
    posts_live = Booking.objects.filter(status__in=["live", "completed"]).count()
    aggregates = PostMetric.objects.aggregate(
        impressions=Sum("impressions"),
        leads=Sum("leads"),
    )
    impressions = aggregates["impressions"] or 0
    leads = aggregates["leads"] or 0
    countries = (
        Creator.objects.values("country").annotate(n=Count("id")).count()
    )
    return [
        _stat(impressions, "Impressions in demo data"),
        _stat(leads, "Leads attributed"),
        _stat(creators, "Creators on Campfire", style="comma"),
        _stat(posts_live, "Posts live or completed", style="comma"),
    ], countries


CREATOR_FEATURES = [
    ("Discover brand deals that match your audience.",
     "Brands find you by audience fit, so the offers that land are ones your followers care about."),
    ("Get paid on time with secure, transparent payouts.",
     "The campaign wallet is funded before you post. No invoice, no chasing."),
    ("See views, clicks and engagement in real time.",
     "Every post carries a tracked link, so you can prove what your audience is worth."),
    ("Manage deals and deliver content with ease.",
     "Accept, decline and submit drafts from one inbox instead of a buried email thread."),
]

CREATOR_TESTIMONIALS = [
    ("Campfire is the marketplace LinkedIn was missing. Clear briefs, fair rates, "
     "and brands that actually match my audience.", "Yasmin Mwangi"),
    ("At first I wasn't sure what to expect. But the whole experience was simple and smooth: "
     "clear opportunities, an easy platform, everything well guided.", "Daniel Fischer"),
    ("Excellent experience. The platform is simple and efficient, and results come fast.",
     "Camille Rossi"),
    ("Great experience — I already made money from day one.", "Raghav Vasquez"),
    ("Campfire lets me keep making useful content while monetizing my LinkedIn community.",
     "Nada Rossi"),
    ("I'd tell every B2B creator to join.", "Felix Djavid"),
]

CREATOR_FAQS = [
    ("What is Campfire?",
     "A B2B LinkedIn creator marketplace. Brands book creators for sponsored posts at a fixed "
     "price per post that you set yourself."),
    ("Is Campfire free for creators?",
     "Yes. Joining costs nothing and you keep what you charge. Brands pay for the campaign."),
    ("How much can I earn?",
     "You set your own price per post. What a brand will pay tracks how well your audience "
     "matches their buyers, not just how large it is."),
    ("How and when do I get paid?",
     "The brand funds the campaign wallet up front, and the payout is released once the post "
     "goes live. You never raise an invoice."),
    ("Do I have to sign an exclusivity contract?",
     "No. You can take deals from anyone, and you can decline any deal without explanation."),
    ("What kind of brands are on Campfire?",
     "B2B software, agencies and services selling to founders, GTM teams and technical buyers."),
    ("Do I keep control of my content?",
     "Always. The brief sets the objective and the things not to say; the words stay yours, "
     "and you can decline a brief that does not fit."),
    ("How do I join?",
     "Sign up as a creator, set your topics, countries and price per post, and you will appear "
     "in brand searches straight away."),
]

AGENCY_TRACKS = [
    {
        "title": "I manage campaigns for companies",
        "body": "Operate separate client workspaces, budgets, campaigns and reporting from one portfolio.",
        "points": ["Create one workspace per client", "Add and allocate client budgets",
                   "Track campaigns and next actions"],
        "cta": "Create a brand agency workspace",
        "featured": True,
    },
    {
        "title": "I represent and manage creators",
        "body": "Import your roster, manage every profile and run collaborations without creator logins.",
        "points": ["Import any creator roster", "Manage rates and creator profiles",
                   "Track collaborations and earnings"],
        "cta": "Create a creator agency workspace",
        "featured": False,
    },
]


def home(request):
    """Public front door. Must look right to a signed-out visitor."""
    creators = Creator.objects.prefetch_related("topics").order_by("-followers")[:6]
    stats, country_count = _live_stats()

    return render(request, "public/home.html", {
        "creators": creators,
        "steps": HOW_IT_WORKS,
        "stats": stats,
        "country_count": country_count,
        "creator_count": Creator.objects.count(),
        "logos": LOGOS,
        "audience": AUDIENCE,
        "testimonial": TESTIMONIAL,
        "fit_preview": FIT_PREVIEW,
        "pipeline_preview": PIPELINE_PREVIEW,
        "bar_preview": BAR_PREVIEW,
        "case_study": CASE_STUDY,
        "posts": EXAMPLE_POSTS,
        "plans": PLANS,
        "faqs": FAQS,
    })


def creators_page(request):
    return render(request, "public/creators.html", {
        "features": CREATOR_FEATURES,
        "testimonials": CREATOR_TESTIMONIALS,
        "faqs": CREATOR_FAQS,
        "posts": EXAMPLE_POSTS,
    })


def agencies_page(request):
    return render(request, "public/agencies.html", {"tracks": AGENCY_TRACKS})


ARTICLES = [
    {
        "title": "Why audience fit beats follower count in B2B",
        "kicker": "PLAYBOOK",
        "body": "A 2,000-follower voice read by forty buyers in your category is worth more "
                "than a 200,000-follower generalist read by nobody who can sign a contract. "
                "Fit is a function of topic overlap, geography and buying role, which is "
                "exactly what the marketplace scores creators on.",
        "minutes": 4,
    },
    {
        "title": "What a creator brief should actually contain",
        "kicker": "GUIDE",
        "body": "The brief is the contract. Objective, key messages, the things a creator "
                "must not say, and a tracked link. Everything else is negotiable, and every "
                "campaign that goes wrong goes wrong because one of those four was vague.",
        "minutes": 6,
    },
    {
        "title": "LinkedIn ads versus creator-led cost per lead",
        "kicker": "BENCHMARK",
        "body": "Paid social buys impressions from an audience that did not ask for you. "
                "Creator posts borrow trust from someone that audience already follows. The "
                "cost per lead usually favours creators; the cost per impression usually "
                "does not. Both numbers matter.",
        "minutes": 5,
    },
]


def blog(request):
    return render(request, "public/blog.html", {"articles": ARTICLES})


def tools(request):
    """Free calculator. The maths runs in the browser, so there is nothing to post."""
    return render(request, "public/tools.html")


def case_study(request):
    return render(request, "public/case_study.html", {"case_study": CASE_STUDY, "posts": EXAMPLE_POSTS})


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")

    return render(request, "auth/signup.html", {"form": form})
