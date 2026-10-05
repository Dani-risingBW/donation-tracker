# 25:35 Fundraiser Tracker

25:35 is a React + Flask fundraiser dashboard for a Washington, D.C. outreach campaign. Public totals include verified donations only; donor submissions enter an admin review queue first.

## Features

- Public 25:35 mission, scripture, progress, and item-drive sections
- Cash and goods donation submissions with server-side validation
- Required private payment screenshots for cash donations, reviewed by admins
- Admin login, approval/rejection queue, and campaign settings
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
| `GET` | `/api/admin/export.csv` | Download verified donations as CSV |
| `POST` | `/api/admin/submissions/<id>/approve` | Approve a pending donation |
| `POST` | `/api/admin/submissions/<id>/reject` | Reject a pending donation |
| `GET` | `/api/admin/submissions/<id>/screenshot` | View a pending screenshot; admin session required |
| `GET` / `PUT` | `/api/admin/settings` | Read or update campaign settings |

The React API client sends JSON and uses `credentials: include` so the admin session cookie is preserved.

## Project structure

```text
app.py                     Flask application, JSON API, and campaign workflows
storage.py                 SQLite state loading and persistence
frontend/                  Vite React client
templates/                 Legacy Flask fallback and admin pages
frontend/src/main.jsx      React application and API client
frontend/src/styles.css    React application styles
tests/test_api.py          API authorization and moderation tests
requirements.txt           Python dependencies
```

## Current limitations

The local app now persists campaign settings, donations, and screenshot metadata in SQLite. Every cash donation requires a payment screenshot; goods donations do not, since items are confirmed at drop-off. Screenshots are stored as generated files under `instance/uploads/`, limited to 1 MB, validated as PNG/JPEG/GIF/WebP, and deleted when approved or rejected. CSRF protection, submission throttling, secure session cookies, and baseline security headers are enabled. Before production launch, add a production authentication provider, external object storage, and a deployment backup/retention process.

## Validation

```bash
python -m py_compile app.py storage.py
pytest -q
cd frontend
npm run build
```

The SQLite database is local application state and should be backed up in deployment. Do not commit the `instance/` directory or production secrets.
