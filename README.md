# Campfire

A B2B LinkedIn creator marketplace for the 8x assignment — **original product UI
and branding**, backed by a real Django database. Built for the rework brief:
own design choices, same marketplace idea, live data (not mock responses).

**Live:** https://muzammalbilal.pythonanywhere.com  
**Repo:** https://github.com/Muzammal-Bilal/naano-clone  
**Demo accounts:** `brand / demo1234` and `creator / demo1234` — also printed on
the login page (one click fills the form).

---

## Product spine

> **Discover creators → build a brief → book them → track what came back.**

| # | Surface | What it does |
| --- | --- | --- |
| 1 | Landing | Campfire brand (Fraunces + Sora, ember palette, SVG flame logo), hero sparks + scroll reveals |
| 2 | Auth | Signup as Brand or Creator; demo logins for both sides |
| 3 | Discover | Search + topic/country/price/followers filters, fit score; HTMX swaps (no full reload) |
| 4 | Campaigns | Brief builder → invite creators → pipeline Invited → … → Completed |
| 5 | Analytics | Impressions, clicks, CTR, leads, pipeline from `PostMetric` (Chart.js) |
| 6 | Creator | Deals inbox, accept/decline, draft submit, earnings ledger |

Homepage marketing stats are **aggregated from the database** (creator count,
metrics sums), not inflated copy.

## Design (own UI, not a site clone)

- Brand name **Campfire**, custom SVG logo (`templates/partials/logo.html`)
- Palette: ink `#12141A`, paper `#F7F3EC`, ember `#E85D04`, charcoal `#1C1F27`
- Motion: hero ember sparks, scroll-in reveals (Alpine), smoother Discover HTMX
  swaps; respects `prefers-reduced-motion`
- No Naano visual language (no sky cloudscape / Plus Jakarta / lookalike chrome)

## Backend (real database)

Django ORM → SQLite locally, Postgres when `DATABASE_URL` is set. App pages
read/write real rows: creators, campaigns, bookings, metrics, transactions.
Server-rendered HTML + HTMX HTML partials (no fake JSON stubs). Wallet/metrics
are demo-grade ledgers/seed curves by design — the tables and CRUD are real.

```bash
python manage.py test core   # 22 tests: access control, ownership, booking lifecycle
```

## Architecture

```
config/     settings, urls, wsgi
core/
  models.py       Creator, Brand, Campaign, Booking, PostMetric, Transaction
  services.py     fit scoring, brief generation
  forms.py        signup, campaign create
  views/          public.py, brand.py, creator.py
  tests.py
  management/commands/seed_demo.py
templates/  base, public/, app/, auth/, partials/ (logo, cards, HTMX results)
.cursor/    hooks for agent capture → .agent-logs/
```

## Running locally

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Scripts/ on Windows, bin/ elsewhere
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed_demo
.venv/Scripts/python manage.py runserver
```

Open http://127.0.0.1:8000/

`seed_demo` builds ~80 creators, 4 campaigns, bookings, and 30 days of metrics
(deterministic). On deploy use `--if-empty` so reviewer signups are not wiped.

### 60-second demo path

1. Open the live site — Campfire landing, sparks, marketplace strip  
2. Sign in as `brand` / `demo1234` → Discover → filter a topic (HTMX)  
3. Campaigns → open a campaign → pipeline  
4. Analytics → chart from DB metrics  
5. Sign out → `creator` / `demo1234` → Deals / Earnings  

## Deploy (PythonAnywhere)

```bash
cd ~/naano-clone
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py seed_demo --if-empty
python manage.py collectstatic --noinput
```

Then **Web → Reload**.

## Agent capture

Prompts and final responses are written automatically into [`.agent-logs/`](.agent-logs)
by a Cursor hook (`project: campfire`). See [CAPTURE-TEST.md](CAPTURE-TEST.md)
for the mechanism and canary verification. Logs from the Campfire redesign
session ship with the repo.
