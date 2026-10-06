# 25:35 Fundraiser Tracker: Implementation Plan

Status: Active implementation. The `feature/2535-fundraiser-buildout` work and the `updated-ui` UI pass were merged into `main` on 2026-10-05 (`main` = `227a868`).

## Current baseline

`main` contains a React/Vite frontend backed by Flask JSON APIs. Campaign settings, verified donations, pending submissions, moderation state, and screenshot metadata persist in a local SQLite store. Public totals are derived only from verified donations; pending submissions remain private to authenticated admins.

**The React app in `frontend/` is the frontend that ships.** The Flask Jinja pages in `templates/` and `static/styles.css` are a legacy fallback: they still use the starter app's green palette and will not get UI or branding updates. Server-side rules in `app.py` still cover both submit routes so behavior stays consistent.

The standalone `25_35 – Fundraiser Tracker.html` remains a visual/behavioral reference. The active implementation replaces its Claude-specific APIs with Flask services, JSON endpoints, SQLite persistence, private screenshot storage, and a React client.

## Implementation status

Completed:

- React/Vite public experience with progress, item drive, donation form, campaign states, and hidden admin entry.
- Flask JSON APIs for campaign data, submissions, admin login, moderation, settings, screenshot review, and CSV export.
- Verified-only aggregation, goods valuation on the server, required screenshot uploads for cash donations, private file storage, and cleanup after moderation.
- SQLite persistence, secure session-cookie defaults, CSRF tokens, submission throttling, security headers, and retry-safe moderation.
- API tests covering authorization, CSRF, rate limiting, screenshots, settings, end states, CSV export, and idempotent approval.
- Protected admin CRUD for manually verified donations and item progress values and targets, with API coverage.
- Sticky header navigation; mobile layout with no horizontal overflow.
- Real Cash App details: `$Spread2535`, with Copy cashtag and Open in Cash App buttons.
- Automated thank-you email to donors when an admin approves their donation.
- Donor confirmation screen after submitting a donation.
- Outreach countdown, campaign close date, and 25/50/75% progress milestones.
- Item Drive "Give this item" shortcut and status highlighting (Almost there / Goal met).
- Planned brand colors and the full Matthew 25:35 verse.

See [Work log: 2026-10-05](#work-log-2026-10-05) for details of each change.

Remaining:

- Fix the known test and data issues listed under [Known issues](#known-issues).
- Replace the lightweight SQLite state adapter with SQLAlchemy models and migrations for production portability.
- Replace the development password with a production identity provider or managed admin accounts.
- Add production object storage, upload retention policy, backups, and deployment configuration.
- Add login throttling, stronger duplicate/replay detection, structured production logging, and a full browser smoke test.
- The Google Forms volunteer link is configured in `VOLUNTEER_FORM_URL` and can be replaced before launch.
- Make the outreach dates editable in admin settings (they are currently code defaults).
- Remaining UI backlog (React only): show form errors next to the form, a friendlier screenshot upload with preview and size check, a Contact section, active-section highlighting in the header, and admin review polish (screenshot thumbnails, pending count, confirm before Reject).
- Confirm the remaining campaign decisions below.

## Product decisions

Confirmed on 2026-10-05:

| Decision | Value |
| --- | --- |
| Cash App cashtag | `$Spread2535` |
| Campaign Gmail and contact email | `spreadmatthew2535@gmail.com` (earlier docs misspelled it "spreadmattew") |
| Outreach dates | November 13–14, 2026 |
| Last day to donate | November 12, 2026; submissions close on November 13 |
| Screenshot requirement | Cash donations only; goods are confirmed at drop-off |
| Thank-you emails | Sent on admin approval, only to donors who gave an email address |
| Shipping frontend | React (`frontend/`); legacy Flask templates are fallback only |
| Production database | Neon PostgreSQL accessed through SQLAlchemy; SQLite remains for local development |
| Production screenshot storage | Private Supabase Storage behind a storage adapter; delete screenshots after moderation |
| Initial hosting tier | Neon and Supabase free tiers for low-traffic launch, with backups and paid resources required before scale |
| Volunteer signup | Configurable Google Forms link; Google manages responses and may require sign-in |
| Tax status | 25:35 is not a registered nonprofit organization; donations are not tax-deductible |
| Application host | Railway, deployed from the reviewed and merged GitHub `main` branch |
| Optional audit analysis | Google Gemini `gemini-3.5-flash-lite` may summarize redacted admin audit metadata; it never replaces the audit log |

Still to confirm before launch:

1. The dollar goal (currently the $1,000 placeholder), item values, item targets, distribution plan, and drop-off instructions.
2. The Google Forms volunteer URL is configured as `https://forms.gle/Ly2nCKeW1kdYKppU6`; it can be replaced through `VOLUNTEER_FORM_URL`.
3. The authentication provider and admin accounts. Recommended default: email/password or an external identity provider with an allowlisted admin role; public donors should not need an account.
4. Production WSGI configuration and Railway environment variables. The deployment target is Railway; see `planning/05-production-decisions.md`.

## Configuration

Secrets live in a git-ignored `.env` file in the project root, loaded by `python-dotenv` when the app starts. `.env.example` is committed and lists every setting without real values.

| Variable | Purpose | Default |
| --- | --- | --- |
| `MAIL_USERNAME` | Gmail account that sends thank-you emails | none (emails are skipped) |
| `MAIL_PASSWORD` | Gmail app password for that account (requires 2-Step Verification) | none (emails are skipped) |
| `MAIL_SENDER_NAME` | Display name on thank-you emails | `Spread 25:35` |
| `VOLUNTEER_FORM_URL` | Google Forms link shown on the site and in thank-you emails | 25:35 volunteer form |
| `DATABASE_URL` | Neon PostgreSQL connection string in production | SQLite fallback locally |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET` | Private Supabase Storage configuration for screenshots | local file storage locally |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional redacted audit analysis; model defaults to `gemini-3.5-flash-lite` | disabled, no API key |
| `ADMIN_PASSWORD`, `SECRET_KEY`, `DATABASE_PATH`, `FRONTEND_ORIGIN` | Existing settings; see README | development values |

Never commit `.env`, the `instance/` directory, or any real password. Rotate the Gmail app password before launch.

## Work log: 2026-10-05

All changes below were made on the `updated-ui` branch (built on `feature/2535-fundraiser-buildout`) and merged into `main` by fast-forward. UI changes were checked in a headless browser at phone (320–390px) and desktop (1280px) widths. Server changes were run against the pytest suite.

### Navigation and layout

- **Sticky header** (`d06dd86`): the top bar stays pinned while scrolling, with a solid full-width background so content scrolls under it. Scroll padding lands the Progress, Item drive, and Donate links with the section heading visible below the header. Scrolling is smooth unless the visitor prefers reduced motion. On phones, the brand and links stay on one row so the header takes less space.
- **Phone overflow fix** (`55ef024`): on narrow screens the Donate section was wider than the screen, so the whole page scrolled sideways. The form fields (especially the file input) and the long contact email kept the grid columns from shrinking. The columns and form fields can now shrink, and long links wrap. No horizontal overflow at 320, 390, or 1280px.

### Cash App giving

- **Real cashtag** (`1d024ac`): `$YourCashtag` replaced with `$Spread2535`. Admins can still change it in settings.
- **Copy cashtag button** (`6378e8f`): copies the cashtag and shows "Copied!". If the browser blocks clipboard access, it tells the donor to press and hold the cashtag instead. The message is announced to screen readers and clears after a few seconds.
- **Open in Cash App button** (`0823689`): links to `cash.app/$Spread2535`, which opens the app on phones and the web page elsewhere. It is built from the campaign cashtag, so it follows admin changes, with or without the leading `$`. It opens in a new tab so donors can return to submit their screenshot.

### Donor thank-you emails

- **Automated thank-you on approval** (`36320e9`): new module `mailer.py`, called from both approval routes in `app.py`.
  - Sent from "Spread 25:35" through the campaign Gmail account over SMTP (port 465, TLS certificate verified).
  - The email names the donor (or "friend" when anonymous) and describes the gift ("$10" or "10 Bottled Water").
  - It shows progress toward the goal including the new gift ("we've raised $X of our $Y goal, with just $Z to go!"), or "we've reached our goal" once the goal is met.
  - It invites the donor to volunteer via `VOLUNTEER_FORM_URL`.
  - Emails go out only on approval, so rejected or fake submissions never get one, and only to donors who gave an email address. The donor's email is not stored on the verified donation record.
  - Sending runs in a background thread and failures are logged, so a slow or failing send never blocks an approval.
  - Credentials come from `.env` (see [Configuration](#configuration)). `python-dotenv==1.0.1` was added to `requirements.txt`, and `.env.example` is exempt from the `.env.*` ignore rule.
  - Tests in `tests/test_email.py` cover the email content for cash, goods, and anonymous donors, the goal-reached and no-volunteer-link variants, skipping when credentials or an address are missing, and the approval flow. `tests/conftest.py` blocks real sends so the suite never contacts Gmail.
  - Verified end to end: a $10 mock donation to a test inbox was approved and the email was delivered.
- **Email address spelling** (`8b27ad8`): the campaign account is `spreadmatthew2535@gmail.com`, but the site, docs, and mockup said "spreadmattew". Donors emailing the old address would not reach anyone. Every copy was corrected.

### Donation flow

- **Confirmation screen** (`4a7bc6f`): before this change, a successful submission only showed a one-line notice at the top of the page, which donors on phones did not see. The form is now replaced in place by a panel that:
  - thanks the donor by name;
  - summarizes the gift ("$10.00" or "10 × Bottled Water");
  - marks it "Pending review";
  - shows where the thank-you email will go;
  - explains what happens next.

  Focus moves to the panel for keyboard and screen reader users. "Submit another donation" brings back a cleared form, and failed submissions keep the form and show the error.
- **Cash-only screenshots** (`3e0dedd`):
  - The server requires a payment screenshot only for cash donations and ignores any file sent with a goods donation, so no image is stored for it.
  - The React form shows the screenshot field only when Cash is selected, and the confirmation tells goods donors their items are confirmed at drop-off.
  - The legacy Flask form had no screenshot field, so its cash submissions always failed; it now has one for cash.
  - A new API test covers goods submissions without screenshots. The README is updated.

### Progress and urgency

- **Outreach countdown** (`3abdb8f`): `event_start` (2026-11-13) and `event_end` (2026-11-14) were added to the campaign.
  - The Progress section shows "N days until our outreach" with "Serving neighbors Nov 13–14, 2026".
  - It counts the donor's local calendar days and switches to "tomorrow", then "happening now" during the event, then a thank-you afterward. Checked on each transition date, including across the Nov 1 daylight-saving change.
  - Campaigns already saved in the database now pick up any new default setting they are missing, so existing data gets the event dates without a reset.
- **Close date** (`943802a`): `end_date` is set to 2026-11-12. Donations are accepted through the end of Nov 12. On Nov 13 the site shows "This fundraiser has ended" and hides the form and the "Give this item" buttons. While open, the countdown adds "Give by Nov 12". The API test fixture clears the end date so tests keep passing after the real campaign closes.
- **Milestones** (`da57a41`):
  - Tick marks at 25/50/75% of the goal with dollar labels ($250 / $500 / $750 for a $1,000 goal). Reached milestones turn gold with a checkmark.
  - A line names the next milestone and the amount left ("Next milestone: $250, just $145.00 to go"). After 75% it switches to "Final stretch", and it disappears once the goal is met.
  - The bar now exposes its value to screen readers.

### Item Drive

- **Give this item** (`bc7fa32`): each card has a button that switches the form to Goods, selects that item, resets the quantity to 1, scrolls to the form, and focuses Quantity. It works from the confirmation screen too, and is hidden once the campaign closes.
- **Status highlighting** (`6feb10c`): items at or past their target get a green "✓ Goal met" badge, card, and bar; items at 75% or more get a gold "Almost there" badge and border. Every item still short shows "N more needed".

### Branding

- **Brand colors** (`8ebd9c6`): the React site now uses the planning document's cream `#F9F6F0`, navy `#001F3F`, and gold `#D99B26`. These are CSS variables (`--cream`, `--navy`, `--gold`) on `:root` in `frontend/src/styles.css`, and the browser theme color matches the navy.
- **Full scripture** (`227a868`): the hero shows the complete verse, ending "…I was a stranger and you invited me in." Both pages now render the campaign's `mission` setting instead of separate hardcoded copies.

## Known issues

- **Two failing tests on `main`** (20 pass, 2 fail):
  - `tests/test_app.py::test_cash_submission_creates_pending_record` is out of date. It submits cash without a screenshot, which is now correctly rejected.
  - `tests/test_api.py::test_admin_can_approve_once_and_retry_safely` fails because of the ID bug below.
- **Submission IDs are reused.** IDs are `submission-{len(pending) + 1}`, so once a submission is approved, the next one gets the same ID (for example, two verified donations are both `submission-1`). Approval retry safety and moderation logging depend on unique IDs, so this should use a UUID or a stored counter.
- **Tests read and write the real local database** (`instance/fundraiser.sqlite3`). The fixture restores state afterward, but local test data can still affect results. Tests should use a temporary `DATABASE_PATH`.
- **Python version:** the README says Python 3.10+, but the app and tests run on 3.9.6 (the macOS system Python). Either document 3.9 as supported or require 3.10 in setup.

## Implementation phases

### 1. Establish the application foundation

- Refactor `app.py` into a small application factory and service-oriented Flask structure while keeping startup simple.
- Add SQLAlchemy models/migrations for `CampaignSettings`, `Item`, `DonationSubmission`, `Donation`, and admin/user records or an external-auth mapping. The current branch uses a temporary SQLite JSON state adapter instead.
- Add configuration from environment variables, a development seed command, structured error handling, CSRF protection, secure cookie settings, and an upload-size limit. Environment loading from `.env` is in place (see [Configuration](#configuration)).
- Add a test configuration and reusable fixtures so public, donor, and admin workflows can be tested without production services, including an isolated test database.

Acceptance criteria:

- A fresh local setup can initialize the database and seed the 25:35 placeholder campaign.
- No public total is derived from unmoderated submissions.
- Secrets and production storage credentials are never committed.

### 2. Build the public 25:35 experience

- Build the public experience in the React app (`frontend/`) using the 25:35 mobile-first visual system: cream background, navy text, gold accent, compact text navigation, scripture, mission, and contact details. Brand colors, the full verse, and the sticky header are done.
- Implement the public sections for Welcome, Progress, Item Drive, Where to Donate, I Donated, and Contact. Use accessible landmarks, labels, focus states, keyboard navigation, responsive layouts, and meaningful empty/error states. Contact is still to do.
- Render only verified donations in public totals and recent activity.
- Add configurable goal, end date, milestone, fundraiser-ended, goal-reached, and remaining-amount states. Milestones, the outreach countdown, and the Nov 12 close date are done.
- Add a configurable impact/distribution section rather than shipping the current placeholder copy.

Acceptance criteria:

- The public page works on narrow mobile and desktop widths without horizontal layout breakage. (Met as of 2026-10-05.)
- Public progress combines verified cash value and verified goods value only.
- Placeholder values (goal, item targets, distribution copy, volunteer link) are replaced or blocked from production deployment.

### 3. Implement item-drive and donor submission workflows

- Add item cards showing collected quantity, target quantity, per-unit value, progress, status, and a shortcut to give that item. (Done.)
- Add a donor form with Cash versus Goods modes. Goods submissions calculate value from the selected item and quantity on the server; client-side calculation is only a convenience.
- Add cash submission fields for amount, optional donor name/email, required payment screenshot, and honeypot/rate-limit controls. Goods submissions do not take a screenshot.
- Validate all fields server-side, normalize names/emails, reject invalid quantities/amounts, and prevent arbitrary item/value injection.
- Store uploaded screenshots in private storage with generated names and metadata, never in public static files or unbounded database fields.
- Provide a clear pending confirmation and avoid exposing pending submission details to public users. (Confirmation screen done.)

Acceptance criteria:

- Every cash submission includes a screenshot that is validated and reviewed privately; goods submissions store no image.
- A cash submission cannot become counted without admin approval.
- Oversized, non-image, malformed, and suspicious uploads are rejected safely.

### 4. Build protected admin moderation and settings

- Add authenticated admin routes for the pending queue, submission detail, approve/reject actions, manual verified entries, campaign settings, and item editing.
- Require authorization on every admin mutation, not only by hiding navigation.
- Make approval transactional and idempotent so retries cannot double-count a donation. This depends on fixing the reused submission IDs.
- On approval, create/update the verified donation record, send the donor thank-you email, and remove or invalidate the screenshot according to the retention policy. On rejection, keep only the minimum audit data required.
- Add audit timestamps, actor identity, status transitions, and optional rejection reasons.
- Add CSV export of verified records with safe escaping and no screenshot data.

Acceptance criteria:

- Anonymous users cannot access admin pages or mutation endpoints.
- A submission appears exactly once in totals after approval.
- Screenshot access is admin-only and no longer available after configured deletion.
- Each approval sends at most one thank-you email, and a failed send never blocks the approval.

### 5. Security, privacy, and operational hardening

- Add CSRF protection, secure session settings, login throttling, request/body limits, upload MIME/content checks, and rate limiting for submissions.
- Add duplicate and replay safeguards using submission metadata and a review warning for suspicious repeated amounts/screenshots where practical.
- Ensure donor email and screenshot URLs are not rendered publicly and are not logged accidentally.
- Add retention controls and document the privacy behavior for screenshots and optional donor contact details, including that donor emails are used only for the thank-you email.
- Add security headers, production logging without sensitive payloads, health checks, and backup/migration guidance.

Acceptance criteria:

- The security test suite covers authorization, CSRF, upload validation, duplicate approval, and public-data leakage.
- The README documents required production secrets (including the mail settings), storage, backups, and retention behavior.

### 6. Verification and launch readiness

- Add unit tests for money/value aggregation, item quantities, progress boundaries, date/ended states, validation, and idempotent approval.
- Add Flask route/integration tests for public pages, donor submissions, admin authorization, approval/rejection, settings, and CSV export.
- Run a browser smoke test at mobile and desktop widths covering Welcome -> Where to Donate -> I Donated -> confirmation -> admin approval -> thank-you email -> updated Progress.
- Add a deployment configuration and production runbook after the hosting decision is confirmed.
- Update README with setup, seed data, test commands, environment variables, admin bootstrap, deployment, and launch checklist.

## Suggested delivery order

1. Fix the known issues (submission IDs, test isolation, out-of-date test).
2. Foundation, models, migrations, configuration, and tests.
3. Remaining public sections (Contact, volunteer sign-up) and UI backlog.
4. Admin authentication, moderation polish, settings (including event dates), and exports.
5. Security/privacy hardening and documentation.
6. Browser verification, deployment configuration, and launch checklist.

## Approval gate

Work now lands on `main`. Use a feature branch per change and keep each logical change in its own commit. The confirmed product decisions above are in effect; the remaining placeholders (goal, item targets, distribution copy, volunteer link) stay in place for development until confirmed.
