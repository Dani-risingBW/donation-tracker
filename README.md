# 25:35 Fundraiser Tracker

25:35 is a React + Flask fundraiser dashboard for a Washington, D.C. outreach campaign. Public totals include verified donations only; donor submissions enter an admin review queue first.

## Features

- Public 25:35 mission, scripture, progress, and item-drive sections
- Cash and goods donation submissions with server-side validation
- Required private payment screenshots for cash donations, reviewed by admins
- Admin login, approval/rejection queue, and campaign settings
- Admin CRUD for verified manual donations and item progress values/targets
- Verified-only public totals and item quantities
- Health endpoint at `/health`
- JSON API consumed by the React client

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in a browser.

The development admin password is `admin123`. Set `ADMIN_PASSWORD` and `SECRET_KEY` in the environment before deployment.
State is stored in `instance/fundraiser.sqlite3` by default. Set `DATABASE_PATH` to use another SQLite file.

For a non-default frontend origin during development, set `FRONTEND_ORIGIN` to the React client URL. The API allows credentialed requests from that origin.

## React development

Start Flask in one terminal:

```bash
python app.py
```

Start the React client in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` requests to Flask. For a production build, run `npm run build`; Flask serves `frontend/dist` automatically when it exists.

## API overview

Public clients can read campaign progress and submit donations without an account:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/campaign` | Campaign settings, verified totals, item progress, and recent verified gifts |
| `POST` | `/api/submissions` | Submit a cash or goods donation for review |
| `GET` | `/health` | Basic service health check |

Admin API calls use the Flask session created by `POST /api/admin/login`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/admin/login` | Start an admin session |
| `GET` | `/api/admin/review` | Read pending and verified donations |
| `POST` | `/api/admin/donations` | Add a verified manual cash or goods donation |
| `PUT` / `DELETE` | `/api/admin/donations/<id>` | Edit or remove a verified donation |
| `GET` | `/api/admin/export.csv` | Download verified donations as CSV |
| `POST` | `/api/admin/submissions/<id>/approve` | Approve a pending donation |
| `POST` | `/api/admin/submissions/<id>/reject` | Reject a pending donation |
| `GET` | `/api/admin/submissions/<id>/screenshot` | View a pending screenshot; admin session required |
| `GET` / `PUT` | `/api/admin/settings` | Read or update campaign settings |

The React API client sends JSON and uses `credentials: include` so the admin session cookie is preserved.

## Production architecture decision

The production database will be **Neon PostgreSQL**, accessed through **SQLAlchemy**. SQLite remains the default for local development because it requires no separate service. PostgreSQL is preferred for production because it handles concurrent writes more reliably and provides a straightforward path to migrations and backups.

Payment screenshots will move from local `instance/uploads/` storage to a **private Supabase Storage bucket** accessed through a storage adapter. Screenshot URLs must never be public; files remain available only to authenticated admins and are deleted after approval or rejection.

The Neon and Supabase free tiers are appropriate for an initial low-traffic launch, but they are not a substitute for a production backup and retention plan. Before the fundraiser depends on the system for important records, enable backups and move to paid resources as needed. Free services may sleep, pause, or impose storage and compute limits.

Production configuration uses `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `SUPABASE_BUCKET`. Never commit these values. See `.env.example` for the configuration template.

## Volunteer signup and tax status

Volunteer registration uses the configured Google Form at https://forms.gle/Ly2nCKeW1kdYKppU6. Set `VOLUNTEER_FORM_URL` in `.env` to replace it; the public site and approved-donation emails link to the configured URL. Google may require volunteers to sign in, and volunteer responses are managed in Google Forms rather than stored by this app.

25:35 is not a registered nonprofit organization. Donations are not tax-deductible.

## Optional audit analysis

The app can optionally use Google Gemini to summarize redacted admin audit metadata. Set `GEMINI_API_KEY` to enable it; the configured model is `gemini-3.5-flash-lite`. The LLM is not the audit log and does not approve or reject donations. Never send donor names, email addresses, payment details, screenshots, request payloads, or secrets to the model.

## Project structure

```text
app.py                     Flask application, JSON API, and campaign workflows
storage.py                 SQLite state loading and persistence
frontend/                  Vite React client
templates/                 Legacy Flask fallback and admin pages
frontend/src/main.jsx      React application and API client
frontend/src/styles.css    React application styles
05-production-decisions.md Railway hosting and production architecture decisions
tests/test_api.py          API authorization and moderation tests
requirements.txt           Python dependencies
```

## Current limitations

The local app currently persists campaign settings, donations, and screenshot metadata in SQLite and stores uploads under `instance/uploads/`. Every cash donation requires a payment screenshot; goods donations do not, since items are confirmed at drop-off. Screenshots are limited to 1 MB, validated as PNG/JPEG/GIF/WebP, and deleted when approved or rejected. CSRF protection, submission throttling, secure session cookies, and baseline security headers are enabled. The production migration to Neon PostgreSQL, SQLAlchemy, and private Supabase Storage remains an implementation step before launch.

## Validation

```bash
python -m py_compile app.py storage.py
pytest -q
cd frontend
npm run build
```

The SQLite database is local application state and should be backed up in deployment. Do not commit the `instance/` directory or production secrets.
