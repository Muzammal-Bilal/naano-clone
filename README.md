# Campfire

A B2B LinkedIn creator marketplace for the 8x assignment — original product UI
and branding, backed by a real Django database. Inspired by the *problem space*
of creator marketplaces; not a visual clone of any existing site.

**Live:** https://muzammalbilal.pythonanywhere.com  
**Demo accounts:** `brand / demo1234` and `creator / demo1234` — both are also
printed on the login page, so no signup is needed to see either side.

---

## What I built, and in what order

A two-sided marketplace needs a spine that makes it a business rather than a directory:

> **Discover creators → build a brief → book them → track what came back.**

1. **Landing page** — Campfire-branded public front door (Fraunces + Sora, ember palette, custom SVG logo).
2. **Auth with two roles** — signup creates either a Brand or a Creator.
3. **Creator marketplace** — search, topic/country/price/audience filters, a fit score, and a detail page. Filters swap via HTMX.
4. **Campaign brief builder** — objective and product description in, structured brief out.
5. **Booking and pipeline** — invite a creator at their price, then move the booking through Invited → Accepted → Draft ready → Scheduled → Live → Completed.
6. **Brand analytics** — impressions, clicks, CTR, leads and attributed pipeline from the `PostMetric` table.
7. **Creator side** — deals inbox, accept/decline, draft submission, earnings ledger.

## Backend (real database, not mocks)

Django ORM over SQLite locally and Postgres when `DATABASE_URL` is set. App pages
query and write real rows: creators, campaigns, bookings, metrics, transactions.
Marketing stats on the homepage are aggregated from the same tables (not inflated
fiction). There is no separate JSON API layer — views render HTML over the ORM
(plus HTMX HTML partials for discover). That is a deliberate choice for surface
area in a short build; the data path is still live.

`python manage.py test core` runs 22 tests covering access control, ownership,
and the booking lifecycle.

## Architecture

```
config/     settings, urls, wsgi
core/
  models.py       domain: Creator, Brand, Campaign, Booking, PostMetric, Transaction
  services.py     fit scoring and brief generation
  forms.py        signup and campaign creation
  views/          public.py, brand.py, creator.py
  tests.py
  management/commands/seed_demo.py
templates/  base, public/, app/, auth/, partials/ (incl. Campfire logo)
```

## Running locally

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Scripts/ on Windows, bin/ elsewhere
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed_demo
.venv/Scripts/python manage.py runserver
```

`seed_demo` builds ~80 creators, 4 campaigns, bookings and 30 days of daily
metrics. It is deterministic. On deploy it runs with `--if-empty` so redeploying
never wipes a reviewer account.

## Agent capture

Prompts and final responses are captured automatically into [`.agent-logs/`](.agent-logs)
by a Cursor hook. See [CAPTURE-TEST.md](CAPTURE-TEST.md).
