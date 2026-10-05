# 25:35 Fundraiser Tracker

25:35 is a React + Flask fundraiser dashboard for a Washington, D.C. outreach campaign. Public totals include verified donations only; donor submissions enter an admin review queue first.

## Features

- Public 25:35 mission, scripture, progress, and item-drive sections
- Cash and goods donation submissions with server-side validation
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

## Project structure

```text
app.py                     Flask application, JSON API, and campaign workflows
frontend/                  Vite React client
templates/index.html       Public 25:35 page
templates/admin*.html      Admin login, review, and settings pages
static/styles.css          Responsive application styles
requirements.txt           Python dependencies
```

## Current limitations

Campaign settings and donations are currently stored in memory and reset when the server restarts. Before production launch, add durable storage, CSRF protection, upload handling for cash receipts, rate limiting, and a production authentication provider.
