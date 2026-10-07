# 25:35 Shipping Plan

This plan lists everything that must happen before the 25:35 site goes live on Railway, in order. It builds on `planning/05-production-decisions.md` and reflects the code as of 2026-10-07.

## Timeline

| Date | Milestone |
| --- | --- |
| 2026-10-07 | Shipping plan written; Decisions 1 and 2 made |
| As soon as ready | Code fixes merged, Railway configured, smoke test passed |
| As soon as ready | Public launch and announcement (no fixed date; ship when Phase 5 passes) |
| 2026-11-12 | Campaign closes (`end_date`) |
| 2026-11-13 to 11-14 | Outreach event |
| After 2026-11-14 | Final export, data cleanup, scale down |

There is no fixed launch date. Ship as soon as the minimum path below is complete, because every day earlier is another day of donations before the campaign closes.

## Current state

- `pytest -q`: 23 passing, 1 failing (`test_admin_can_approve_once_and_retry_safely`), caused by the duplicate submission ID bug below.
- Memory is not a constraint: about 28 MB idle and about 42 MB with 10,000 donations. A single process can handle roughly 300 to 500 visitors at the same time, which is far more than this campaign needs.
- `DATABASE_URL` and the `SUPABASE_*` variables are documented but not used anywhere in the code. Production would currently write to local SQLite and `instance/uploads/`.
- Railway's container filesystem is wiped on every deploy. Without a volume, donations and screenshots would be lost.

## Decision 1: How cash donations are collected

**Decided (2026-10-07): Option B.** GoFundMe is the main way to give cash. Cash App stays on the site as a secondary, fee-free option.

**Option A: keep the current manual flow.** Donors pay through Cash App, upload a screenshot, and an admin approves each one. There are no platform fees, but every item in Phase 1 is required and an admin has to check the queue every day.

**Option B: GoFundMe for cash, the site for everything else.** Cash donations go through a GoFundMe link or embed. The site keeps the story, the goods drive, item progress, volunteer signup, and the About page. This removes screenshot uploads, cash moderation, and most of the security risk. The trade-offs are card processing fees (roughly 3% per donation; confirm current rates), donors leaving the site to give, and payouts going to one organizer's personal bank account. Cash App can stay as an optional fee-free alternative, recorded by admins as manual donations.

Follow-up decisions (2026-10-07):

- The GoFundMe campaign is https://gofund.me/901ac545b.
- The site links to GoFundMe with a donate button rather than embedding its widget.
- Admins enter GoFundMe and Cash App gifts by hand as manual donations, so they count toward the one progress bar. The site no longer accepts cash submissions or payment screenshots.
- The goods donation form is the only form the public fills out.
- Donor emails are kept after the campaign so 25:35 can tell donors about future events.

## Decision 2: Where production data lives

**Decided (2026-10-07): Option A.** The campaign is not expected to pass 1,000 users.

**Option A: Railway volume.** Keep SQLite and local uploads, and mount a Railway volume at `/data`. This is a config change only.

**Option B: Neon PostgreSQL plus Supabase Storage.** This matches `05-production-decisions.md`, but it needs SQLAlchemy models, migrations, and a storage adapter that are not built yet.

Update the README and `05-production-decisions.md` to match.

## Phase 1: Code fixes

**Status (2026-10-07):** all items done on the `preparing-for-shipping` branch. Item 6 was already fixed. Item 3 is handled by the production entry point `backend/wsgi.py`, so the gunicorn command is `gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT backend.wsgi:app`. The duplicate admin panel on the home page (`?admin=1`) was removed; `/admin` is the only admin page and now has a sign-out button.

All items are in scope, including the ones marked Recommended.

| # | Issue | Location | Fix | Required |
| --- | --- | --- | --- | --- |
| 1 | Submission IDs use `len(pending_submissions) + 1` and repeat after moderation. The local database already has six verified donations with the ID `submission-1`. | `backend/app.py` (`api_submit_donation`, `submit_donation`) | Generate IDs with `uuid4().hex` | Yes |
| 2 | Seed donations ("Amina O.", "Jordan L.") count toward the public total. | `backend/app.py`, `verified_donations` | Start with an empty list | Yes |
| 3 | `SECRET_KEY` falls back to `dev-secret-key` and `ADMIN_PASSWORD` to `admin123`. | `backend/app.py` | Refuse to start in production without both | Yes |
| 4 | Behind Railway's proxy, every request shares one IP, so the submission rate limit applies to all donors together. | `backend/app.py`, `allow_submission` | Wrap the app with `werkzeug.middleware.proxy_fix.ProxyFix` | Yes |
| 5 | There is no production WSGI server, and `app.run(debug=True)` must not run in production. | `requirements.txt` | Add `gunicorn`; start with `gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT backend.app:app` | Yes |
| 6 | `"start": "http-server"` is referenced but not installed, and Railway may run it instead of Flask. | `frontend/package.json` | Remove the script | Yes |
| 7 | Every frontend dependency is pinned to `"latest"`. | `frontend/package.json` | Pin to the versions in `package-lock.json`; build with `npm ci` | Recommended |
| 8 | Request threads change shared state without a lock. | `backend/app.py` | Wrap changes and `persist_state()` in a `threading.Lock` | Recommended |
| 9 | Admin login has no limit on password attempts. | `/api/admin/login` | Limit to 5 attempts per minute per IP | Recommended |
| 10 | The legacy Flask form routes (`/submissions`, `/admin/approve`, and others) skip the CSRF check. React is the shipping frontend. | `backend/app.py`, `templates/` | Remove the legacy routes and templates | Recommended |
| 11 | Screenshot upload and storage, cash moderation | `backend/app.py`, `frontend/src/` | Remove; cash is entered by admins as manual donations | Yes |

| 12 | GoFundMe is not on the site yet. | `frontend/src/main.jsx`, `backend/app.py` (`campaign`) | Add a `gofundme_url` campaign setting (`https://gofund.me/901ac545b`) and a prominent donate button, with Cash App shown as secondary | Yes |
| 13 | The goal is still the $1,000 placeholder. | `backend/app.py` (`campaign`) | Set `goal` to `2000.0` | Yes |

**The app must run with exactly one gunicorn worker** while state lives in process memory. Multiple workers would each hold separate copies of the data and overwrite each other's saves.

## Phase 2: Tests and local data

1. Done: `tests/conftest.py` points `DATABASE_PATH` at a temporary directory before `backend.app` is imported.
2. Done: tests cover unique submission IDs, the login attempt limit, per-visitor rate limits, email privacy, and startup failure when secrets are missing.
3. Done: deleted the old local `instance/` test database and uploads.
4. Upgrade the local environment to Python 3.12 (the current `.venv` is 3.9.6, and the README requires 3.10+). `.python-version` (3.12) is added, and the Docker image uses Python 3.12.
5. Confirm that `pytest -q` and `npm run build` both pass, then merge to `main` through a PR.

## Phase 3: Railway setup

**Status (2026-10-07):** the `Dockerfile`, `.dockerignore`, and `railway.json` are in the repo. `railway.json` sets the Dockerfile build, one replica, the `/health` health check, and restart on failure, so steps 2 and 5 need no dashboard changes. The remaining steps are done in the Railway dashboard.

1. Create a Railway project on the Hobby plan and connect the GitHub repo to deploy from `main`.
2. Add a `Dockerfile` so the build runs both Node and Python:
   - Stage 1: `cd frontend && npm ci && npm run build`
   - Stage 2: copy `frontend/dist`, `pip install -r requirements.txt`, start gunicorn with `backend.wsgi:app`
3. Attach a volume at `/data` (Decision 2 Option A).
4. Set the environment variables:

   ```env
   SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
   ADMIN_PASSWORD=<strong unique password>
   COOKIE_SECURE=1
   DATABASE_PATH=/data/fundraiser.sqlite3
   MAIL_USERNAME=spreadmatthew2535@gmail.com
   MAIL_PASSWORD=<Gmail app password>
   MAIL_SENDER_NAME=Spread 25:35
   VOLUNTEER_FORM_URL=<final Google Form URL>
   ```

   Leave out `GEMINI_API_KEY`, because `backend/llm_audit.py` is not connected to any route yet. Leave out `FRONTEND_ORIGIN`, because the API and the site share one origin.
5. Set the health check path to `/health`.
6. Buy `matt2535.net`, add it as a custom domain in Railway, set the DNS records Railway gives, and confirm that HTTPS works and HTTP redirects to it.
7. Set a usage limit in Railway billing (Malachi, at launch).

## Phase 4: Content and legal review

1. Confirm the goal ($2,000; may still change), item values and targets, end date (2026-11-12), and event dates (2026-11-13 to 11-14).
2. Verify the GoFundMe link and the cashtag `$Spread2535` character by character.
3. The not-tax-deductible notice in both footers was checked on 2026-10-07: "We are not a registered nonprofit organization. Donations are not tax-deductible." No change needed.
4. Add a short privacy note covering what is collected (names and emails), why, that emails may be used to announce future 25:35 events, and a contact email. Any future event email needs an unsubscribe option.
5. Send a test thank-you email and review the wording and volunteer link. The volunteer Google Form URL on this branch is final.
6. Proofread the home and About pages.

## Phase 5: Production smoke test

Run these on the Railway URL, on both a phone and a desktop.

- [ ] The GoFundMe button or embed opens the correct campaign
- [ ] `/health` returns `{"status": "ok"}`; `/` and `/about` load
- [ ] A goods submission shows as pending, and the public totals are unchanged
- [ ] Invalid goods input is rejected (missing item, quantity of zero)
- [ ] The page has no cash submission form or screenshot upload
- [ ] Admin login works with the new password, and `admin123` is rejected
- [ ] Approving updates the totals and sends the thank-you email (check spam)
- [ ] Rejecting removes the submission
- [ ] A manual GoFundMe or Cash App donation entered by an admin updates the public total
- [ ] CSV export works; manual donations can be added, edited, and deleted
- [ ] **After a redeploy, all data is still there**
- [ ] Rate limiting blocks only the device sending too many submissions
- [ ] All test donations are deleted before the announcement

## Phase 6: Running the campaign

- **Backups:** export the CSV daily and copy the SQLite file off the volume weekly.
- **Monitoring:** enable Railway deploy and crash notifications, and add an uptime check on `/health`.
- **Moderation:** the developers share the admin password and check the review queue (at least twice a day).
- **Changes during the campaign:** only through branch and PR. Know how to roll back a deploy in Railway.
- **Email:** Gmail allows about 500 messages a day, which is enough for this campaign.

## Phase 7: After the campaign

1. Download the final CSV and SQLite backup.
2. Delete any remaining pending submissions.
3. Keep donor names and emails for future event announcements; store the final export somewhere only organizers can reach.
4. Scale down or remove the Railway service.

## Minimum path to launch

Phase 1 items 1 to 6 and 11 to 13, Phase 2 items 1, 3, and 5, all of Phase 3, Phase 4 items 1 and 2, and Phase 5.
