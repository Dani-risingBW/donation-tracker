# 25:35 Production Decisions

> **Superseded in part (2026-10-07).** `06-shipping-plan.md` replaces the Neon PostgreSQL and Supabase Storage choices below. Production uses SQLite on a Railway volume, and the site no longer accepts payment screenshots: cash goes through GoFundMe or Cash App and admins enter it by hand. The Railway hosting decision still stands.

## Hosting decision

25:35 will be hosted on **Railway**. Railway will run the Flask application and serve the built React frontend. The application will deploy from the GitHub `main` branch after changes are reviewed and merged through pull requests.

## Production architecture

```text
Donor browser
    |
    v
Railway: Flask API + built React frontend
    |                 |                  |
    v                 v                  v
Neon PostgreSQL   Supabase Storage   Gmail SMTP
campaign data     private screenshots thank-you emails
```

- **Railway:** application hosting, HTTPS endpoint, deployment, runtime logs, environment variables, and health checks.
- **Flask:** API, donation validation, admin sessions, moderation workflows, and public verified totals.
- **React/Vite:** public fundraiser experience, built during deployment and served by Flask from `frontend/dist`.
- **Neon PostgreSQL:** production relational database accessed through SQLAlchemy. SQLite remains for local development only.
- **Supabase Storage:** private storage for payment screenshots. Screenshots are served only to authenticated admins through short-lived access and deleted after moderation.
- **Gmail SMTP:** optional donor thank-you email delivery.
- **Google Forms:** volunteer signup and response collection. Volunteer responses are not stored in this application.

## Why Railway

Railway is a good fit for this application because it reduces the infrastructure we need to manage while keeping deployment connected to the repository.

- **GitHub-based deployments:** a merged pull request can trigger a repeatable deployment without manually copying files to a server.
- **Simple Flask deployment:** Railway supports Flask services and can run the app with a production WSGI command such as `gunicorn backend.app:app`.
- **One place for runtime configuration:** production values such as `DATABASE_URL`, `GEMINI_API_KEY`, `SECRET_KEY`, and mail credentials can be stored as Railway environment variables instead of committed to GitHub.
- **Deployment history and rollback:** Railway keeps deployment history, making it easier to identify a bad release and return to a known working deployment.
- **Runtime visibility:** logs, deployment status, service health, and resource usage are available from the Railway dashboard.
- **HTTPS and public service URL:** Railway provides a public HTTPS endpoint, with the option to add a custom domain later.
- **Clear path from pilot to production:** the project can start small and increase service resources as traffic and moderation activity grow.
- **Separation of concerns:** Railway runs the app, while Neon and Supabase provide managed data services. This avoids treating a container filesystem as permanent storage.

## Cost and free-tier position

Railway's Free plan is intended for experimentation and includes limited monthly usage. It should not be treated as a permanent production guarantee. The initial production target is the Railway Hobby plan, currently listed as a $5/month subscription that counts toward resource usage. Actual cost can increase with CPU, memory, storage, and network use.

Neon and Supabase may also begin on their free tiers for a low-traffic launch. Those tiers can pause, sleep, or impose storage and compute limits, and may not include the backup and retention features needed for important records. Before the fundraiser depends on the system, enable backups and move to paid resources where required.

## Railway environment variables

Configure these in Railway's service Variables settings. Do not commit real values to GitHub.

```env
SECRET_KEY=<long-random-production-secret>
ADMIN_PASSWORD=<temporary-development-only-password-to-replace>
DATABASE_URL=<Neon PostgreSQL connection string>
SUPABASE_URL=<Supabase project URL>
SUPABASE_SERVICE_KEY=<private Supabase service key>
SUPABASE_BUCKET=payment-screenshots
GEMINI_API_KEY=<optional Gemini API key>
GEMINI_MODEL=gemini-3.5-flash-lite
MAIL_USERNAME=<optional Gmail sender>
MAIL_PASSWORD=<Gmail app password>
MAIL_SENDER_NAME=Spread 25:35
VOLUNTEER_FORM_URL=https://docs.google.com/forms/d/e/1FAIpQLSfingNyaQYAfLHCKJTrau8OozUlUEV-haxXMNalJy93zLrbeA/viewform
COOKIE_SECURE=1
```

`GEMINI_API_KEY` is optional. If it is absent, audit analysis remains disabled and the application continues to work. Only redacted audit metadata may be sent to Gemini. Never send donor names, email addresses, payment details, screenshots, request payloads, or secrets to the model.

## Deployment workflow

1. Develop on a feature branch.
2. Run backend tests and the frontend production build locally.
3. Push the feature branch to GitHub.
4. Open a pull request into `main`.
5. Review the code and checks before merging.
6. Railway deploys the merged `main` branch.
7. Verify `/health`, the public campaign page, donation submission, and admin login after deployment.

## Production requirements before launch

- Replace the development admin password with managed admin authentication.
- Add SQLAlchemy models and migrations for Neon PostgreSQL.
- Add the Supabase Storage adapter and private signed access for screenshots.
- Configure database backups and screenshot retention/deletion policies.
- Add a production WSGI start command and health-check configuration.
- Set a custom domain and confirm HTTPS behavior.
- Run a browser smoke test on mobile and desktop.
- Confirm the campaign goal, item targets, distribution details, and tax notice.

## Nonprofit and tax notice

25:35 is not a registered nonprofit organization. Donations are not tax-deductible. This notice must remain visible on the public site and should be reviewed with appropriate local legal or tax guidance before launch.
