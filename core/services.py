"""Business logic that is not CRUD.

Kept out of views so both the marketplace and the seed command score fit the
same way.
"""

from decimal import Decimal


def fit_score(creator, topic_ids, countries, budget=None):
    """Score a creator against a brand's ICP, out of 100.

    Naano surfaces this as "MATCHING 92/100". Weighted so topic overlap
    dominates, because audience relevance is the thing that actually predicts
    whether a B2B post converts. Deliberately a pure function of already-loaded
    data: no queries, so it can run over a whole page of creators.
    """
    score = Decimal("40")  # floor, so a vetted creator is never scored at zero

    creator_topics = {topic.id for topic in creator.topics.all()}
    if topic_ids:
        overlap = len(creator_topics & set(topic_ids)) / len(topic_ids)
        score += Decimal(str(overlap)) * 35
    else:
        score += 20

    if countries:
        score += 15 if creator.country.upper() in countries else 0
    else:
        score += 8

    # Engagement matters more than raw reach for B2B.
    score += min(creator.engagement_rate, Decimal("6")) * 2

    if budget and creator.price_per_post > budget:
        score -= 12

    return max(0, min(100, int(score)))


BRIEF_TEMPLATES = {
    "awareness": (
        "Introduce {company} to your audience in your own voice.",
        "Lead with the problem, not the product. Name the category before the tool.",
    ),
    "pipeline": (
        "Show your audience how {company} removes a real bottleneck in their week.",
        "Anchor on a concrete before-and-after. Vague benefit claims do not convert.",
    ),
    "signups": (
        "Walk through the first five minutes of using {company}.",
        "End on the single next step. One link, one action.",
    ),
    "hiring": (
        "Talk about how the team behind {company} actually works.",
        "Write it as a personal observation, not a job advert.",
    ),
}


def generate_brief(company, objective, product_description=""):
    """Draft a campaign brief from structured inputs.

    Template-driven on purpose: no API key, no latency, no spend, and it cannot
    fail mid-demo. Swapping in an LLM call means replacing this one function.
    """
    angle, guidance = BRIEF_TEMPLATES.get(objective, BRIEF_TEMPLATES["pipeline"])
    summary = angle.format(company=company)

    messages = [summary]
    if product_description:
        messages.append(f"Context to work from: {product_description.strip()}")

    dos = [
        "Write in your own voice, the one your audience already follows you for.",
        "Use a specific example, number, or story from your own experience.",
        "Disclose the partnership clearly.",
    ]
    donts = [
        "Do not paste marketing copy verbatim.",
        "Do not stack more than one call to action.",
        "Do not post without the tracked link.",
    ]

    return {
        "key_messages": "\n".join(messages),
        "guidelines": guidance,
        "dos": "\n".join(dos),
        "donts": "\n".join(donts),
    }
