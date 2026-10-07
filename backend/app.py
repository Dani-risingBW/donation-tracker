import logging
import os
import csv
import io
import secrets
import threading
import time
from pathlib import Path
from datetime import date, datetime
from uuid import uuid4

from flask import Flask, jsonify, make_response, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix

from . import mailer
from .storage import load_state, save_state


PROJECT_ROOT = Path(__file__).parent.parent
app = Flask(__name__, static_folder=None)
# Railway's proxy adds one X-Forwarded-For hop; trust it so rate limits see each visitor's own IP.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

DEFAULT_ITEMS = [
    {"id": "beanies", "name": "Knit Beanies", "value": 8, "target": 50},
    {"id": "mittens", "name": "Warm Mittens", "value": 6, "target": 50},
    {"id": "scarves", "name": "Fleece Scarves", "value": 10, "target": 40},
    {"id": "sandwiches", "name": "Cold Sandwiches", "value": 4, "target": 100},
    {"id": "fruit", "name": "Fruit Cups & Granola Bars", "value": 2, "target": 100},
    {"id": "water", "name": "Bottled Water", "value": 1, "target": 200},
    {"id": "hygiene", "name": "Hygiene Kits", "value": 5, "target": 60},
    {"id": "bags", "name": "Drawstring Bags", "value": 3, "target": 60},
]

campaign = {
    "name": "25:35",
    "description": "Serving our unhoused neighbors in Washington, D.C. through practical care, prayer, and joyful outreach.",
    "mission": "For I was hungry and you gave me something to eat, I was thirsty and you gave me something to drink, I was a stranger and you invited me in.",
    "scripture": "Matthew 25:35",
    "goal": 2000.0,
    "gofundme_url": "https://gofund.me/901ac545b",
    "cashtag": "$Spread2535",
    "end_date": "2026-11-12",
    "event_start": "2026-11-13",
    "event_end": "2026-11-14",
    "items": [item.copy() for item in DEFAULT_ITEMS],
    "distribution": "Gifts support direct outreach and practical care for neighbors in need throughout the DC area.",
    "contact_email": "spreadmatthew2535@gmail.com",
}

verified_donations = []
pending_submissions = []
moderation_log = {}
rate_limit_attempts = {}
# Gunicorn runs one worker with several threads; every change to shared state holds this lock.
state_lock = threading.RLock()
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

state = load_state({
    "campaign": campaign,
    "verified_donations": verified_donations,
    "pending_submissions": pending_submissions,
    "moderation_log": moderation_log,
})
# Campaigns saved before a setting existed pick up its default.
for key, value in campaign.items():
    state["campaign"].setdefault(key, value)
campaign = state["campaign"]
verified_donations = state["verified_donations"]
pending_submissions = state["pending_submissions"]
moderation_log = state.get("moderation_log", {})


def persist_state():
    save_state({
        "campaign": campaign,
        "verified_donations": verified_donations,
        "pending_submissions": pending_submissions,
        "moderation_log": moderation_log,
    })


def get_item(item_id):
    return next((item for item in campaign["items"] if item["id"] == item_id), None)


def total_raised():
    return sum(float(donation["value"]) for donation in verified_donations)


def item_totals():
    totals = {}
    for donation in verified_donations:
        if donation["type"] == "goods" and donation.get("item_id"):
            item_id = donation["item_id"]
            totals[item_id] = totals.get(item_id, 0) + donation["quantity"]
    return totals


def thank_donor(submission):
    mailer.send_thank_you(submission, submission.get("email", ""), total_raised(), float(campaign["goal"]))


def admin_required():
    return bool(session.get("admin_logged_in"))


def allow_attempt(bucket, maximum, window):
    key = (bucket, request.remote_addr or "unknown")
    now = time.monotonic()
    with state_lock:
        attempts = [attempt for attempt in rate_limit_attempts.get(key, []) if now - attempt < window]
        allowed = len(attempts) < maximum
        if allowed:
            attempts.append(now)
        rate_limit_attempts[key] = attempts
        return allowed


def allow_submission():
    return allow_attempt(
        "submission",
        int(os.environ.get("SUBMISSION_RATE_LIMIT", "10")),
        float(os.environ.get("SUBMISSION_RATE_WINDOW", "60")),
    )


def allow_login():
    return allow_attempt("login", int(os.environ.get("LOGIN_RATE_LIMIT", "5")), 60.0)


def positive_float(value, fallback):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def positive_int(value, fallback):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def campaign_status():
    if campaign.get("end_date"):
        try:
            if date.today() > date.fromisoformat(campaign["end_date"]):
                return "ended"
        except ValueError:
            pass
    if total_raised() >= float(campaign["goal"]):
        return "goal_reached"
    return "active"


def clean_email(value):
    email = str(value or "").strip()[:160]
    if email and "@" not in email:
        raise ValueError("Enter a valid email address or leave it blank.")
    return email


def public_donation(donation):
    # Donor emails are kept for future event announcements and never shown publicly.
    return {key: value for key, value in donation.items() if key != "email"}


def public_payload():
    raised = total_raised()
    goal = float(campaign["goal"])
    public_campaign = {
        **campaign,
        "volunteer_form_url": os.environ.get(
            "VOLUNTEER_FORM_URL", "https://docs.google.com/forms/d/e/1FAIpQLSfingNyaQYAfLHCKJTrau8OozUlUEV-haxXMNalJy93zLrbeA/viewform"
        ).strip(),
    }
    return {
        "campaign": public_campaign,
        "donations": [public_donation(donation) for donation in verified_donations],
        "totalRaised": raised,
        "progress": min((raised / goal) * 100, 100) if goal else 0,
        "remaining": max(goal - raised, 0),
        "donorCount": len(verified_donations),
        "itemTotals": item_totals(),
        "adminSession": admin_required(),
        "campaignStatus": campaign_status(),
    }


@app.after_request
def add_api_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.path.startswith("/api/"):
        response.headers["Access-Control-Allow-Origin"] = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@app.before_request
def protect_api_mutations():
    if request.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = session.get("csrf_token")
        provided = request.headers.get("X-CSRF-Token", "")
        if not expected or not secrets.compare_digest(expected, provided):
            return jsonify({"error": "Missing or invalid CSRF token."}), 403


@app.route("/api/csrf")
def api_csrf():
    token = session.setdefault("csrf_token", secrets.token_urlsafe(32))
    return jsonify({"token": token})


@app.route("/api/campaign", methods=["GET"])
def api_campaign():
    with state_lock:
        return jsonify(public_payload())


@app.route("/api/submissions", methods=["POST", "OPTIONS"])
def api_submit_donation():
    """Record a pledged goods donation; cash gifts go through GoFundMe or Cash App and are entered by admins."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not allow_submission():
        return jsonify({"error": "Too many submissions. Please try again later."}), 429
    data = request.get_json(silent=True) or {}
    if data.get("honeypot"):
        return jsonify({"error": "Submission rejected."}), 400
    if data.get("type", "goods") != "goods":
        return jsonify({"error": "Give cash through GoFundMe or Cash App. This form is for goods only."}), 400
    item = get_item(data.get("itemId") or data.get("item_id"))
    quantity = positive_int(data.get("quantity"), 0)
    if not item or quantity <= 0:
        return jsonify({"error": "Choose a valid item and quantity."}), 400
    try:
        email = clean_email(data.get("email"))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    name = str(data.get("name") or "Anonymous").strip()[:80] or "Anonymous"
    submission = {
        "id": f"submission-{uuid4().hex}", "name": name, "email": email, "type": "goods",
        "item_id": item["id"], "item_name": item["name"], "quantity": quantity,
        "value": item["value"] * quantity, "date": datetime.today().strftime("%Y-%m-%d"),
    }
    with state_lock:
        if campaign_status() != "active":
            return jsonify({"error": "This fundraiser is no longer accepting submissions."}), 409
        pending_submissions.insert(0, submission)
        persist_state()
    return jsonify({"message": "Thank you. Your donation is pending review."}), 201


@app.route("/api/admin/login", methods=["POST", "OPTIONS"])
def api_admin_login():
    if request.method == "OPTIONS":
        return ("", 204)
    if not allow_login():
        return jsonify({"error": "Too many sign-in attempts. Wait a minute and try again."}), 429
    data = request.get_json(silent=True) or {}
    password = str(data.get("password", ""))
    if not secrets.compare_digest(password.encode(), os.environ.get("ADMIN_PASSWORD", "admin123").encode()):
        return jsonify({"error": "Incorrect password."}), 401
    session["admin_logged_in"] = True
    return jsonify({"authenticated": True})


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"authenticated": False})


@app.route("/api/admin/review", methods=["GET"])
def api_admin_review():
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    with state_lock:
        return jsonify({"pending": pending_submissions, "verified": verified_donations})


def admin_donation_from_data(data, existing=None):
    """Validate and normalize a manually managed verified donation."""
    existing = existing or {}
    donation_type = data.get("type", existing.get("type", "cash"))
    name = str(data.get("name", existing.get("name", "Anonymous"))).strip()[:80] or "Anonymous"
    donation = {
        "id": existing.get("id", f"manual-{uuid4().hex}"),
        "name": name,
        "type": donation_type,
        "date": str(data.get("date", existing.get("date", date.today().isoformat()))),
        "email": clean_email(data.get("email", existing.get("email", ""))),
    }
    try:
        date.fromisoformat(donation["date"])
    except ValueError as error:
        raise ValueError("Date must use YYYY-MM-DD format.") from error

    if donation_type == "cash":
        value = positive_float(data.get("value", data.get("amount", existing.get("value", 0))), 0)
        if value <= 0:
            raise ValueError("Cash value must be greater than zero.")
        donation["value"] = value
    elif donation_type == "goods":
        item = get_item(data.get("itemId", data.get("item_id", existing.get("item_id"))))
        quantity = positive_int(data.get("quantity", existing.get("quantity", 0)), 0)
        if not item or quantity <= 0:
            raise ValueError("Choose a valid item and quantity greater than zero.")
        donation.update({
            "item_id": item["id"],
            "item_name": item["name"],
            "quantity": quantity,
            "value": item["value"] * quantity,
        })
    else:
        raise ValueError("Donation type must be cash or goods.")
    return donation


@app.route("/api/admin/donations", methods=["POST"])
def api_admin_create_donation():
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    try:
        donation = admin_donation_from_data(request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    with state_lock:
        verified_donations.insert(0, donation)
        persist_state()
        return jsonify(public_payload()), 201


@app.route("/api/admin/donations/<donation_id>", methods=["PUT", "DELETE"])
def api_admin_manage_donation(donation_id):
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    with state_lock:
        donation = next((entry for entry in verified_donations if entry["id"] == donation_id), None)
        if not donation:
            return jsonify({"error": "Donation not found."}), 404
        if request.method == "DELETE":
            verified_donations.remove(donation)
            persist_state()
            return jsonify(public_payload())
        try:
            updated = admin_donation_from_data(request.get_json(silent=True) or {}, donation)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        donation.clear()
        donation.update(updated)
        persist_state()
        return jsonify(public_payload())


@app.route("/api/admin/export.csv")
def api_admin_export():
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "name", "email", "type", "value", "item", "quantity", "date"])
    with state_lock:
        for donation in verified_donations:
            writer.writerow([
                donation.get("id", ""), donation.get("name", ""), donation.get("email", ""),
                donation.get("type", ""), donation.get("value", ""), donation.get("item_name", ""),
                donation.get("quantity", ""), donation.get("date", ""),
            ])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=verified-donations.csv"
    return response


@app.route("/api/admin/submissions/<submission_id>/<action>", methods=["POST"])
def api_admin_moderate(submission_id, action):
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    if action not in {"approve", "reject"}:
        return jsonify({"error": "Unsupported moderation action."}), 400
    with state_lock:
        submission = next((entry for entry in pending_submissions if entry["id"] == submission_id), None)
        if not submission and submission_id in moderation_log:
            return jsonify(public_payload())
        if not submission:
            return jsonify({"error": "Submission not found."}), 404
        if action == "approve":
            verified_donations.insert(0, dict(submission))
        moderation_log[submission_id] = action + "d"
        pending_submissions.remove(submission)
        persist_state()
        payload = public_payload()
    if action == "approve":
        thank_donor(submission)
    return jsonify(payload)


@app.route("/api/admin/settings", methods=["GET", "PUT"])
def api_admin_settings():
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    if request.method == "GET":
        with state_lock:
            return jsonify({"campaign": campaign})
    data = request.get_json(silent=True) or {}
    gofundme_url = str(data.get("gofundmeUrl") or campaign["gofundme_url"]).strip()
    if not gofundme_url.startswith("https://"):
        return jsonify({"error": "The GoFundMe link must start with https://."}), 400
    end_date = str(data.get("endDate", campaign["end_date"]))
    if end_date:
        try:
            date.fromisoformat(end_date)
        except ValueError:
            return jsonify({"error": "End date must use YYYY-MM-DD format."}), 400
    with state_lock:
        updated_items = campaign["items"]
        if "items" in data:
            incoming_items = data["items"]
            if not isinstance(incoming_items, list) or {item.get("id") for item in incoming_items} != {item["id"] for item in campaign["items"]}:
                return jsonify({"error": "Items must include every existing item exactly once."}), 400
            updated_items = []
            for current in campaign["items"]:
                incoming = next(item for item in incoming_items if item.get("id") == current["id"])
                value = positive_float(incoming.get("value"), 0)
                target = positive_int(incoming.get("target"), 0)
                if value <= 0 or target <= 0:
                    return jsonify({"error": "Item values and targets must be greater than zero."}), 400
                updated_items.append({**current, "value": value, "target": target})
        campaign["goal"] = positive_float(data.get("goal"), campaign["goal"])
        campaign["gofundme_url"] = gofundme_url
        campaign["cashtag"] = str(data.get("cashtag") or campaign["cashtag"]).strip()
        campaign["end_date"] = end_date
        campaign["distribution"] = str(data.get("distribution") or campaign["distribution"]).strip()
        campaign["items"] = updated_items
        persist_state()
        return jsonify({"campaign": campaign})


def react_page():
    if (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return ("The frontend has not been built. Run npm run build in frontend/.", 503)


@app.route("/")
def dashboard():
    return react_page()


@app.route("/about")
def about_page():
    return react_page()


@app.route("/admin")
def admin_dashboard():
    return react_page()


@app.route("/assets/<path:filename>")
def frontend_asset(filename):
    return send_from_directory(FRONTEND_DIST / "assets", filename)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)
