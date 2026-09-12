# Naano clone

A rebuild of [naano.com](https://naano.com), the B2B LinkedIn creator marketplace,
for the 8x assignment. Not affiliated with Naano.

**Live:** _pending deploy_
**Demo accounts:** `brand / demo1234` and `creator / demo1234` — both are also
printed on the login page, so no signup is needed to see either side.

---

## What I built, and in what order

Naano is a two-sided marketplace, and you cannot rebuild both sides properly in a
day. I picked the spine that makes the product a business rather than a directory:

> **Discover creators → build a brief → book them → track what came back.**

1. **Landing page** — the public front door. A reviewer who is not signed in
   still has to land on something that looks like the product.
2. **Auth with two roles** — signup creates either a Brand or a Creator.
3. **Creator marketplace** — search, topic/country/price/audience filters, a fit
   score, and a detail page. Filters swap via HTMX, so nothing reloads.
4. **Campaign brief builder** — objective and product description in, structured
   brief out.
5. **Booking and pipeline** — invite a creator at their price, then move the
   booking through Invited → Accepted → Draft ready → Scheduled → Live → Completed.
6. **Brand analytics** — impressions, clicks, CTR, leads and attributed pipeline,
   charted daily and broken down per campaign.
7. **Creator side** — deals inbox, accept/decline, draft submission, earnings ledger.

## What I deliberately left out

Each of these is a decision, not an oversight.

| Cut | Why |
| --- | --- |
| LinkedIn OAuth and real publishing | Needs a LinkedIn partner app and review. Days of waiting, zero visible product. |
| Stripe payments and real payouts | The wallet is a ledger that records movement without moving money. Real payments would consume the whole budget for one screen. |
| Real UTM click tracking | Attribution infrastructure is a product in itself. Metrics are seeded from a decay curve that matches how a post actually behaves. |
| The Managed (€700/mo) tier | It is a services offering, not software. Nothing to build. |
| Blog, SEO pages, help centre | Content surface. No engineering signal. |
| Email and notifications | Needs a provider and deliverability setup to demo honestly. |
| Drag-and-drop pipeline | A dropdown drives the same state machine with far less code, and works on a phone. |

**What I would build next, in order:** campaign editing after creation, a
shortlist so creators can be compared before committing budget, real click
tracking behind the existing `landing_url`, and brand-side draft approval, which
today is implicit when a booking moves past Draft ready.

## Architecture

Django rendering HTML on the server, no API layer and no client framework. For a
one-day build judged on working surface area, a SPA would have spent hours on
plumbing that buys nothing a reviewer can see.

```
config/     settings, urls, wsgi
core/
  models.py       domain: Creator, Brand, Campaign, Booking, PostMetric, Transaction
  services.py     fit scoring and brief generation
  forms.py        signup and campaign creation
  views/          public.py, brand.py, creator.py
  management/commands/seed_demo.py
templates/  base, public/, app/, auth/, partials/
```

Decisions worth explaining:

- **No `role` column.** A user is a creator or a brand based on which profile row
  points at them. A role field can drift out of sync with the data; this cannot.
- **Fit score is a pure function.** Topic overlap against the brand's ICP is a set
  operation the ORM cannot express cheaply, so filtering happens in SQL and only
  the narrowed set is scored in Python.
- **The brief generator is template-driven, not an LLM call.** No API key, no
  latency, no spend, and it cannot fail mid-demo. Swapping in a model call means
  replacing one function in `services.py`.
- **Seeded metrics decay.** Impressions fall off geometrically after publishing,
  which is what makes the analytics chart read as real rather than as noise.
- **Tailwind and Chart.js from CDNs.** There is no Node on the build machine, so
  a bundler step would have been a dependency to install before writing any code.

## Running locally

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Scripts/ on Windows, bin/ elsewhere
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed_demo
.venv/Scripts/python manage.py runserver
```

`seed_demo` builds 80 creators, 4 campaigns, their bookings and 30 days of daily
metrics. It is deterministic, so the demo is identical on every machine. On
deploy it runs with `--if-empty` so redeploying never wipes an account a reviewer
just created.

## Agent capture

Prompts and final responses are captured automatically into [`.agent-logs/`](.agent-logs)
by a Cursor hook. See [CAPTURE-TEST.md](CAPTURE-TEST.md) for the mechanism and the
canary verification.
