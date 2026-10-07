# 25:35 Fundraiser Tracker

25:35 is a React + Flask fundraiser dashboard for a Washington, D.C. outreach campaign. Money is given through GoFundMe (main) or Cash App, and admins record each gift by hand. The public form is for goods pledges only, which enter an admin review queue. Public totals include verified donations only.

## Features

- Public 25:35 mission, scripture, progress, and item-drive sections
- GoFundMe donate button, with Cash App as a fee-free alternative
- Goods pledge form with server-side validation
- Admin login, goods approval/rejection queue, and campaign settings
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
python -m backend.app
```

Open http://127.0.0.1:5000 in a browser.

The Flask backend source lives in `backend/`; run it from the repository root so its package imports and project paths resolve correctly.

The development admin password is `admin123`. Set `ADMIN_PASSWORD` and `SECRET_KEY` in the environment before deployment.
State is stored in `instance/fundraiser.sqlite3` by default. Set `DATABASE_PATH` to use another SQLite file.

For a non-default frontend origin during development, set `FRONTEND_ORIGIN` to the React client URL. The API allows credentialed requests from that origin.

## React development

Start Flask in one terminal:

```bash
python -m backend.app
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
| `POST` | `/api/submissions` | Pledge a goods donation for review |
| `GET` | `/health` | Basic service health check |

Admin API calls use the Flask session created by `POST /api/admin/login`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/admin/login` | Start an admin session (5 attempts per minute per IP) |
| `POST` | `/api/admin/logout` | End the admin session |
| `GET` | `/api/admin/review` | Read pending and verified donations |
| `POST` | `/api/admin/donations` | Add a verified manual cash or goods donation |
| `PUT` / `DELETE` | `/api/admin/donations/<id>` | Edit or remove a verified donation |
| `GET` | `/api/admin/export.csv` | Download verified donations, including donor emails, as CSV |
| `POST` | `/api/admin/submissions/<id>/approve` | Approve a pending donation |
| `POST` | `/api/admin/submissions/<id>/reject` | Reject a pending donation |
| `GET` / `PUT` | `/api/admin/settings` | Read or update campaign settings |

The React API client sends JSON and uses `credentials: include` so the admin session cookie is preserved.

## Production architecture decision

Production runs on Railway with SQLite on a Railway volume mounted at `/data` (`DATABASE_PATH=/data/fundraiser.sqlite3`). The campaign is expected to stay under 1,000 users, so a managed database is not needed. See `planning/06-shipping-plan.md` for the full launch checklist.

Start the app in production with:

```bash
gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT backend.wsgi:app
```

`backend.wsgi` refuses to start unless `SECRET_KEY` and `ADMIN_PASSWORD` are set to real values. Run exactly one worker: state lives in process memory, and several workers would overwrite each other's saves.

## Volunteer signup and tax status

Volunteer registration uses the configured Google Form at https://docs.google.com/forms/d/e/1FAIpQLSfingNyaQYAfLHCKJTrau8OozUlUEV-haxXMNalJy93zLrbeA/viewform. Set `VOLUNTEER_FORM_URL` in `.env` to replace it; the public site and approved-donation emails link to the configured URL. Google may require volunteers to sign in, and volunteer responses are managed in Google Forms rather than stored by this app.

25:35 is not a registered nonprofit organization. Donations are not tax-deductible.

## Optional audit analysis

The app can optionally use Google Gemini to summarize redacted admin audit metadata. Set `GEMINI_API_KEY` to enable it; the configured model is `gemini-3.5-flash-lite`. The LLM is not the audit log and does not approve or reject donations. Never send donor names, email addresses, payment details, screenshots, request payloads, or secrets to the model.

## Project structure

```text
backend/app.py             Flask application, JSON API, and campaign workflows
backend/wsgi.py            Production entry point that checks secrets
backend/storage.py         SQLite state loading and persistence
backend/mailer.py          Donor thank-you email delivery
backend/llm_audit.py       Optional redacted Gemini audit analysis
frontend/                  Vite React client
planning/                  Product, implementation, production, and visual reference documents
frontend/src/main.jsx      React application and API client
frontend/src/styles.css    React application styles
planning/05-production-decisions.md Railway hosting and production architecture decisions
tests/test_api.py          API authorization and moderation tests
requirements.txt           Python dependencies
```

## Current limitations

Campaign settings and donations are persisted in SQLite. GoFundMe and Cash App gifts are not detected automatically; admins enter them as manual donations. Donor emails are kept for future 25:35 event announcements, are visible only to admins and in the CSV export, and are never included in the public API. CSRF protection, per-visitor submission throttling, admin login throttling, secure session cookies, and baseline security headers are enabled.

## Validation

```bash
python -m py_compile backend/app.py backend/storage.py backend/mailer.py backend/llm_audit.py
pytest -q
cd frontend
npm run build
```

The SQLite database is local application state and should be backed up in deployment. Do not commit the `instance/` directory or production secrets.
