# Gather & Co.

An event-rental **inventory and reservation website** built with Django. Customers browse the inventory (with product images), check live availability for their dates and reserve items through bookings. The owner posts products, reviews bookings and confirms or declines them. Every page includes an AI support assistant that answers from verified FAQ and error-code data.

| | |
|---|---|
| **Live website** | _Pending: added after the Render deployment is verified (see Deployment)._ |
| **GitHub repository** | https://github.com/jkishoresubha-crypto/gather-and-co |
| **Health check** | `/health/` |

---

## Features

- **Inventory catalogue**: 14 seeded rental products in 6 categories, each with an illustration. Search, category filter and a date-range availability check.
- **Bookings**: signed-in customers reserve a quantity for a date range. Availability is calculated from overlapping pending/confirmed bookings, and the product row is locked during booking to prevent overbooking. Customers see an estimated total, get a `BK-XXXXXX` reference, track status in **My bookings** and can cancel.
- **Owner dashboard** (`/owner/`): booking statistics, status filters, confirm / decline / complete with a note, post new products and edit existing ones with photo upload (JPEG/PNG/WebP, validated with Pillow and stored in PostgreSQL so photos survive redeploys).
- **FAQ page**: 31 FAQs stored in PostgreSQL covering accounts, browsing, availability, booking rules and statuses, pricing, the owner dashboard, privacy, the assistant, error codes and support,, with category labels, search and category filter.
- **Error code reference**: 400, 401, 403, 404, 429, 500, 503 and the site-specific application code **4600 AI_ASSISTANT_UNAVAILABLE**, each with meaning, common causes, troubleshooting steps and next action. The page is searchable.
- **AI assistant on every page**: retrieval-first answers grounded in the FAQ, error-code and product data. It creates a support ticket when it cannot answer, accepts thumbs up/down feedback, and falls back to plain FAQ text (clearly labelled, code 4600) when the AI provider is unavailable.
- **Support tickets**: a public form plus one-click tickets from the assistant, stored in PostgreSQL and managed only in Django Admin.
- **MongoDB Atlas**: chat logs and feedback, with graceful degradation when MongoDB is unreachable.
- **OpenWeather**: an "Event-day weather" card on the home page, with timeouts, caching and fallbacks.
- **Custom 404 / 500 pages** with an *Ask the assistant* button that opens the chat with the error context.
- **Request logging middleware** and a **health endpoint**.

## Demo accounts

Created by `python manage.py seed_demo`:

| Role | Username | Password | Can do |
|---|---|---|---|
| Owner (staff + admin) | `owner` | `GatherOwner#2026` | Owner dashboard, post/edit products, confirm bookings, Django Admin |
| Customer | `customer` | `GatherGuest#2026` | Reserve items, view/cancel own bookings (has sample bookings) |
| Customer | `jordan` | `GatherGuest#2026` | Second customer with sample bookings |

> These are public demo credentials for assessment testing only. On a real deployment set `DEMO_OWNER_PASSWORD` / `DEMO_CUSTOMER_PASSWORD` before the first seed, or change the passwords in Django Admin.

## Technology stack

Python 3.11 · Django 5.2 LTS · Django templates · HTML5 · CSS3 · Bootstrap 5.3 · vanilla JavaScript · PostgreSQL (psycopg 3) · MongoDB Atlas (PyMongo 4) · OpenAI Chat Completions API · OpenWeather API · WhiteNoise · Gunicorn · Render · Git/GitHub

All versions are pinned in `requirements.txt`.

## Architecture

```
Browser ──HTTPS──> Gunicorn + Django (Render web service)
                     ├── PostgreSQL (Render): products, bookings, users, FAQs, error codes, tickets
                     ├── MongoDB Atlas: chat_logs, feedback          (optional, degrades gracefully)
                     ├── OpenAI API: answer generation (server-side) (optional, FAQ fallback)
                     └── OpenWeather API: weather card (server-side) (optional, friendly fallback)
```

All third-party calls happen on the server. No API key is ever sent to the browser.

## Project structure

```
config/            settings (env-driven), urls, wsgi
core/              home page, sign-up, weather client, rate limiter, form mixin, 404/500 handlers
inventory/         Category / Product / Booking models, catalogue, booking flow, owner dashboard, seed_demo command
faqs/              FAQ + ErrorCode models, FAQ & error-code pages, seed_data.py, seed_faqs command
assistant/         chat / ticket / feedback endpoints, retrieval.py, llm.py (AI provider), mongo.py
support/           SupportTicket model, support form, confirmation page, admin
monitoring/        request-logging middleware, health-check middleware and view
templates/         base layout, chat widget include, pages, 404.html, 500.html
static/            css/site.css, js/chat.js, img/products/*.svg
tests/             automated test suite (63 tests)
build.sh           Render build script
render.yaml        Render Blueprint (web service + PostgreSQL)
```

The chat widget is a reusable include (`templates/includes/chat_widget.html`) rendered by `base.html`, so every page that extends the base layout gets it. Error pages pass `chat_context` so the assistant knows the visitor hit a 404 or 500.

## Local installation

```bash
git clone <repository-url>
cd gather-and-co
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Edit `.env` and set at least `DJANGO_SECRET_KEY`. `.env` is git-ignored and is for local development only.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes (prod) | Django secret key. Startup fails with a clear error if it is missing while DEBUG is off |
| `DJANGO_DEBUG` | no | `True` locally, `False` in production (default `False`) |
| `DJANGO_ALLOWED_HOSTS` | yes (prod) | Comma-separated hosts. Render's hostname is added automatically |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | no | Extra trusted origins, e.g. a custom domain |
| `DATABASE_URL` | yes (prod) | PostgreSQL URL. Startup fails if it is missing while DEBUG is off |
| `MONGODB_URI` / `MONGODB_DATABASE` | no | MongoDB Atlas connection for chat logs and feedback |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | no | AI provider (default model `gpt-4o-mini`) |
| `OPENWEATHER_API_KEY` / `DEFAULT_WEATHER_CITY` | no | Weather card |
| `DEMO_OWNER_PASSWORD` / `DEMO_CUSTOMER_PASSWORD` | no | Passwords for the demo accounts on first seed |
| `PORT` | Render | Port Gunicorn binds to (set by Render) |

### PostgreSQL setup

Production always uses PostgreSQL through `DATABASE_URL`. Locally you can either:

- set `DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/gather_co` after creating the database (`createdb gather_co`), or
- leave `DATABASE_URL` empty while `DJANGO_DEBUG=True`, in which case Django uses a local SQLite file **for development and tests only**. SQLite is refused when DEBUG is off.

### MongoDB setup

1. Create a free MongoDB Atlas cluster, a database user and a network-access rule (`0.0.0.0/0` for Render, or Render's outbound IPs).
2. Copy the `mongodb+srv://…` connection string into `MONGODB_URI` (locally in `.env`, in production in Render's Environment settings).
3. Collections `chat_logs` and `feedback` are created automatically on first insert.

When MongoDB is not configured or unreachable, the website keeps working. Chat logging and feedback storage are skipped, a warning is logged (without connection details), MongoDB is skipped for 60 seconds, and `/health/` reports `"mongodb": "unavailable"` with status `degraded`.

### Migrations, seeding and running

```bash
python manage.py migrate
python manage.py seed_demo        # FAQs, error codes, products, demo accounts, sample bookings (idempotent)
python manage.py seed_faqs        # only FAQs + error codes (idempotent)
python manage.py runserver
```

Both seed commands use `update_or_create` / `get_or_create`, so running them repeatedly never creates duplicates. Sample bookings are only created when no bookings exist.

### Running the automated tests

```bash
python manage.py test
```

The tests mock all external services (OpenAI, OpenWeather, MongoDB), so they need no paid API or network access. They run against a temporary SQLite database. The PostgreSQL-specific code path (row locking, `DATABASE_URL` parsing) runs in production. Test areas:

pages and chat widget on every page · FAQ retrieval from the database · FAQ search/filter · seed idempotency · all 8 error codes · custom 404 · custom 500 (via a test-only URLconf, so production has no crash endpoint) · booking create/overbooking/validation/cancel · status mass-assignment protection · owner permissions and confirmations · product photo upload validation · support ticket create/invalid input/rate limit · AI answer grounded in retrieved FAQs · AI fallback on missing key/timeout/HTTP error · ticket creation for unanswerable questions · undocumented codes not guessed · MongoDB logging, feedback and failure handling · OpenWeather caching/timeout/429/404/malformed/missing key · health endpoint (ok/degraded/503) · request logging without query strings · chat rate limiting · CSRF on chat · missing `DJANGO_SECRET_KEY` / `DATABASE_URL` · production security settings.

**Latest result:** `Ran 63 tests ... OK` (local run on Windows, Python 3.11.7, 29 Oct 2026).

## AI assistant workflow

1. The browser posts the question (max 500 characters, 4 KB body) with the CSRF token to `/assistant/chat/`. The endpoint is rate limited to 12 requests per minute per client.
2. **Error-code detection**: numbers such as `404` / `4600` and names such as "forbidden" are matched against the `ErrorCode` table.
3. **Retrieval**: the question is tokenised (stop-words removed), active FAQs and products are pre-filtered in the database with ORM `icontains` queries, and each candidate is scored. A term in the question or keywords scores 1, a term found only in the answer scores 0.25, and the score is normalised by the number of terms.
4. **Relevance threshold**: results below `ASSISTANT_RELEVANCE_THRESHOLD` (default 0.34) or below 60% of the best score are dropped. If nothing remains and no error code matched, the assistant says it is not sure and offers a support ticket. It does not call the AI or guess. Codes that are not documented, such as 418, are refused the same way.
5. **Generation**: only the retrieved FAQ, error-code and product facts are sent to the AI model, with a system prompt forbidding invented policies, records or explanations.
6. **Fallback**: if the key is missing or the provider times out or errors, the retrieved FAQ and error-code text is shown directly with the notice *AI_ASSISTANT_UNAVAILABLE (4600)*. It is never presented as AI output.
7. **Logging**: each exchange is stored in MongoDB `chat_logs` (pseudonymous conversation ID from the session, question, answer, FAQ IDs, error codes, source, ticket flag). Ratings from 1 to 5 with an optional comment of up to 500 characters go to `feedback`.

**AI provider:** OpenAI Chat Completions (`OPENAI_API_KEY`, `OPENAI_MODEL`), called with `requests` and a 5 s connect / 20 s read timeout.

## Error-code reference

| Code | Name | Type |
|---|---|---|
| 400 | Bad Request | HTTP status |
| 401 | Unauthorized | HTTP status |
| 403 | Forbidden | HTTP status |
| 404 | Not Found | HTTP status |
| 429 | Too Many Requests | HTTP status |
| 500 | Internal Server Error | HTTP status |
| 503 | Service Unavailable | HTTP status |
| 4600 | AI_ASSISTANT_UNAVAILABLE | **Application code (not HTTP)** |

HTTP status codes are the web standard attached to every response. **4600** is specific to Gather & Co. It appears inside a normal (HTTP 200) chat response when the AI service cannot answer.

## Third-party API: timeouts and fallback

`core/weather.py` calls OpenWeather on the server with a `(3.05 s connect, 5 s read)` timeout. City names are validated with a regex, and results are cached for 10 minutes. HTTP 404, 429, 401/403 and other non-200 responses, malformed JSON, timeouts and a missing key each produce a friendly message such as *"Live weather is temporarily unavailable"*. Weather values are never invented.

## Security measures

- Secrets come only from environment variables. `.env` is git-ignored, and `.env.example` contains placeholders.
- `DEBUG` defaults to off. Production refuses to start without `DJANGO_SECRET_KEY` and `DATABASE_URL`.
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are set from the environment plus Render's hostname. Unknown hosts get HTTP 400.
- Production uses HTTPS redirect, secure + HttpOnly session/CSRF cookies, HSTS (1 hour by default, `DJANGO_HSTS_SECONDS`), `X-Frame-Options: DENY`, `nosniff`, and a same-origin referrer policy.
- CSRF protection on every form and on the JSON chat endpoints. There is no CORS, because the API is same-origin only.
- Django ORM only, no raw SQL. Forms whitelist their fields: ticket status/priority and booking status/reference cannot be set by visitors. Owner status changes follow an allowed-transition table.
- Rate limits: chat 12/min, tickets 5 per 10 min, bookings 10 per 10 min (per client IP, cache-based).
- Uploads are limited to 2 MB, verified as real JPEG/PNG/WebP (SVG/HTML rejected), and served with a `default-src 'none'` CSP.
- The owner dashboard requires staff/Owners-group membership (403 otherwise). Django Admin requires a staff login. There is no public ticket dashboard.
- Logs record method, path, status and duration only: no query strings, bodies, cookies, headers or keys. MongoDB errors log the exception type only.
- Error pages never show tracebacks or settings. The 500 handler is tested without a public crash endpoint.

> If a real secret is ever committed by mistake, deleting it in a later commit is **not enough**. Revoke or rotate the key at the provider immediately, then clean the repository history (e.g. `git filter-repo`) if needed.

## Deployment (Render)

The repository includes a **Render Blueprint** (`render.yaml`) that creates:

- `gather-co`: a Python web service. Build: `./build.sh` (install, `collectstatic`, `migrate`, `seed_demo`). Start: Gunicorn. Health check: `/health/`.
- `gather-co-db`: a managed PostgreSQL database, wired to `DATABASE_URL`.
- `DJANGO_SECRET_KEY` is generated by Render. `DEBUG=False`.

Steps:

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, select the repository and approve. Or open `https://render.com/deploy?repo=<github-repo-url>`.
3. When prompted, enter the optional secrets `MONGODB_URI`, `OPENAI_API_KEY` and `OPENWEATHER_API_KEY` in Render. They can be left empty and added later under *Environment*.
4. Wait for the build, then open the `onrender.com` URL and `/health/`.
5. **Superuser:** the seeded `owner` account is already a superuser. To create your own, open the service **Shell** in Render and run `python manage.py createsuperuser`.

Notes: Render's free instances sleep when idle, so the first request can take about a minute. Free PostgreSQL databases expire after a limited period; check Render's current plan terms or upgrade for long-term use. Product photos and tickets live in PostgreSQL and chat logs in MongoDB, so nothing depends on the ephemeral filesystem.

## Screenshots

_To be added: screenshots taken from the deployed site (home, inventory, booking, owner dashboard, chat, 404)._

## Proposed future improvement

**Semantic search over a larger verified knowledge base.** Replace the keyword-overlap scorer with embeddings (e.g. PostgreSQL `pgvector`) over FAQs, product descriptions and rental policies, while keeping the relevance threshold and the "answer only from retrieved facts" rule. The assistant would then understand paraphrases such as "can I give the chairs back a day late?" that share no keywords with the stored answers.
