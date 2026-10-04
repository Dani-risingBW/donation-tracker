# GiveTrack

GiveTrack is a starter fundraising tracker built with Flask. It provides a simple campaign dashboard showing progress toward a goal, donor activity, and a quick form for recording donations.

## Features

- Campaign goal and progress summary
- Total donors and average donation metrics
- Recent donation activity
- Donation entry form with validation
- Responsive desktop and mobile layout

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

## Project structure

```text
app.py              Flask application and starter data
templates/index.html Dashboard page
static/styles.css   Responsive application styles
requirements.txt    Python dependencies
```

## Next steps

The starter currently stores donations in memory, so entries reset when the server restarts. A production version should add a database, authentication, campaign management, payment processing, and environment-based configuration.
