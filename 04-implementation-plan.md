# 25:35 Fundraiser Tracker: Implementation Plan

Status: Active implementation on `feature/2535-fundraiser-buildout`

## Current baseline

The branch now contains a React/Vite frontend backed by Flask JSON APIs. Campaign settings, verified donations, pending submissions, moderation state, and screenshot metadata persist in a local SQLite store. Public totals are derived only from verified donations; pending submissions remain private to authenticated admins.

The standalone `25_35 – Fundraiser Tracker.html` remains a visual/behavioral reference. The active implementation replaces its Claude-specific APIs with Flask services, JSON endpoints, SQLite persistence, private screenshot storage, and a React client.

## Implementation status

Completed:

- React/Vite public experience with progress, item drive, donation form, campaign states, and hidden admin entry.
- Flask JSON APIs for campaign data, submissions, admin login, moderation, settings, screenshot review, and CSV export.
- Verified-only aggregation, goods valuation on the server, required screenshot uploads, private file storage, and cleanup after moderation.
- SQLite persistence, secure session-cookie defaults, CSRF tokens, submission throttling, security headers, and retry-safe moderation.
- API tests covering authorization, CSRF, rate limiting, screenshots, settings, end states, CSV export, and idempotent approval.

Remaining:

- Replace the lightweight SQLite state adapter with SQLAlchemy models and migrations for production portability.
- Replace the development password with a production identity provider or managed admin accounts.
- Add production object storage, upload retention policy, backups, and deployment configuration.
- Add login throttling, stronger duplicate/replay detection, structured production logging, and a full browser smoke test.
- Confirm campaign-specific product decisions: real cashtag, goal, dates, item targets, distribution language, tax language, and deployment target.

## Product decisions to confirm before implementation

1. Confirm the real Cash App cashtag, dollar goal, end date, item values, item targets, distribution plan, drop-off instructions, and tax-deductibility language.
2. Choose the production persistence and file-storage path. Recommended default: SQLite for local/development and PostgreSQL plus private object storage for production, accessed through SQLAlchemy and a storage adapter.
3. Confirm the authentication provider and admin accounts. Recommended default: email/password or an external identity provider with an allowlisted admin role; public donors should not need an account.
4. Confirm deployment target and environment-variable strategy. The app should support local Flask execution and a production WSGI server.

## Implementation phases

### 1. Establish the application foundation

- Refactor `app.py` into a small application factory and service-oriented Flask structure while keeping startup simple.
- Add SQLAlchemy models/migrations for `CampaignSettings`, `Item`, `DonationSubmission`, `Donation`, and admin/user records or an external-auth mapping. The current branch uses a temporary SQLite JSON state adapter instead.
- Add configuration from environment variables, a development seed command, structured error handling, CSRF protection, secure cookie settings, and an upload-size limit.
- Add a test configuration and reusable fixtures so public, donor, and admin workflows can be tested without production services.

Acceptance criteria:

- A fresh local setup can initialize the database and seed the 25:35 placeholder campaign.
- No public total is derived from unmoderated submissions.
- Secrets and production storage credentials are never committed.

### 2. Build the public 25:35 experience

- Replace the starter GiveTrack content in `templates/index.html` and `static/styles.css` with the 25:35 mobile-first visual system from the prompt and reference artifact: cream background, navy text/menu, gold accent, compact text navigation, scripture, mission, and contact details.
- Implement the public sections/routes for Welcome, Progress, Item Drive, Where to Donate, I Donated, and Contact. Use accessible landmarks, labels, focus states, keyboard navigation, responsive layouts, and meaningful empty/error states.
- Render only verified donations in public totals and recent activity.
- Add configurable goal, end date, milestone, fundraiser-ended, goal-reached, and remaining-amount states.
- Add a configurable impact/distribution section rather than shipping the current placeholder copy.

Acceptance criteria:

- The public page works on narrow mobile and desktop widths without horizontal layout breakage.
- Public progress combines verified cash value and verified goods value only.
- Placeholder cashtag/instructions are visibly marked for replacement or blocked from production deployment.

### 3. Implement item-drive and donor submission workflows

- Add item cards showing collected quantity, target quantity, per-unit value, and progress.
- Add a donor form with Cash versus Goods modes. Goods submissions calculate value from the selected item and quantity on the server; client-side calculation is only a convenience.
- Add cash submission fields for amount, optional donor name/email, required screenshot, and honeypot/rate-limit controls.
- Validate all fields server-side, normalize names/emails, reject invalid quantities/amounts, and prevent arbitrary item/value injection.
- Store uploaded screenshots in private storage with generated names and metadata, never in public static files or unbounded database fields.
- Provide a clear pending confirmation and avoid exposing pending submission details to public users.

Acceptance criteria:

- Every donor submission includes a screenshot that is validated and reviewed privately.
- A cash submission cannot become counted without admin approval.
- Oversized, non-image, malformed, and suspicious uploads are rejected safely.

### 4. Build protected admin moderation and settings

- Add authenticated admin routes for the pending queue, submission detail, approve/reject actions, manual verified entries, campaign settings, and item editing.
- Require authorization on every admin mutation, not only by hiding navigation.
- Make approval transactional and idempotent so retries cannot double-count a donation.
- On approval, create/update the verified donation record and remove or invalidate the screenshot according to the retention policy. On rejection, keep only the minimum audit data required.
- Add audit timestamps, actor identity, status transitions, and optional rejection reasons.
- Add CSV export of verified records with safe escaping and no screenshot data.

Acceptance criteria:

- Anonymous users cannot access admin pages or mutation endpoints.
- A submission appears exactly once in totals after approval.
- Screenshot access is admin-only and no longer available after configured deletion.

### 5. Security, privacy, and operational hardening

- Add CSRF protection, secure session settings, login throttling, request/body limits, upload MIME/content checks, and rate limiting for submissions.
- Add duplicate and replay safeguards using submission metadata and a review warning for suspicious repeated amounts/screenshots where practical.
- Ensure donor email and screenshot URLs are not rendered publicly and are not logged accidentally.
- Add retention controls and document the privacy behavior for screenshots and optional donor contact details.
- Add security headers, production logging without sensitive payloads, health checks, and backup/migration guidance.

Acceptance criteria:

- The security test suite covers authorization, CSRF, upload validation, duplicate approval, and public-data leakage.
- The README documents required production secrets, storage, backups, and retention behavior.

### 6. Verification and launch readiness

- Add unit tests for money/value aggregation, item quantities, progress boundaries, date/ended states, validation, and idempotent approval.
- Add Flask route/integration tests for public pages, donor submissions, admin authorization, approval/rejection, settings, and CSV export.
- Run a browser smoke test at mobile and desktop widths covering Welcome -> Where to Donate -> I Donated -> pending -> admin approval -> updated Progress.
- Add a deployment configuration and production runbook after the hosting decision is confirmed.
- Update README with setup, seed data, test commands, environment variables, admin bootstrap, deployment, and launch checklist.

## Suggested delivery order

1. Foundation, models, migrations, configuration, and tests.
2. Public 25:35 pages and verified-only aggregation.
3. Goods and cash submission workflows with private uploads.
4. Admin authentication, moderation, settings, and exports.
5. Security/privacy hardening and documentation.
6. Browser verification, deployment configuration, and launch checklist.

## Approval gate

The implementation is proceeding on the dedicated `feature/2535-fundraiser-buildout` branch. Product decisions above remain launch inputs; placeholder campaign values are intentionally retained for development until confirmed.