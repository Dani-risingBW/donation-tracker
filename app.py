import logging
import os
import csv
import io
import secrets
import time
from pathlib import Path
from datetime import date, datetime
from uuid import uuid4

from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

import mailer
from storage import load_state, save_state


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
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
    "mission": "For I was hungry and you gave me something to eat, I was thirsty and you gave me something to drink.",
    "scripture": "Matthew 25:35",
    "goal": 1000.0,
    "cashtag": "$Spread2535",
    "end_date": "",
    "items": [item.copy() for item in DEFAULT_ITEMS],
    "distribution": "Gifts support direct outreach and practical care for neighbors in need throughout the DC area.",
    "contact_email": "spreadmattew2535@gmail.com",
}

verified_donations = [
    {"id": "seed-1", "name": "Amina O.", "type": "cash", "value": 75.0, "date": "2026-09-28"},
    {"id": "seed-2", "name": "Jordan L.", "type": "goods", "item_id": "water", "item_name": "Bottled Water", "quantity": 10, "value": 10.0, "date": "2026-09-26"},
]
pending_submissions = []
moderation_log = {}
submission_attempts = {}
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", Path(__file__).parent / "instance" / "uploads"))
MAX_SCREENSHOT_BYTES = 1 * 1024 * 1024
SCREENSHOT_TYPES = {
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ("jpg", b"\xff\xd8\xff"),
    "image/gif": ("gif", b"GIF8"),
    "image/webp": ("webp", b"RIFF"),
}

state = load_state({
    "campaign": campaign,
    "verified_donations": verified_donations,
    "pending_submissions": pending_submissions,
    "moderation_log": moderation_log,
})
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


def money(value):
    return f"${float(value):,.2f}"


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


def allow_submission(client_id):
    now = time.monotonic()
    window = float(os.environ.get("SUBMISSION_RATE_WINDOW", "60"))
    maximum = int(os.environ.get("SUBMISSION_RATE_LIMIT", "10"))
    attempts = [attempt for attempt in submission_attempts.get(client_id, []) if now - attempt < window]
    if len(attempts) >= maximum:
        submission_attempts[client_id] = attempts
        return False
    attempts.append(now)
    submission_attempts[client_id] = attempts
    return True


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


def save_screenshot(upload):
    if not upload or not upload.filename:
        return None
    raw = upload.read(MAX_SCREENSHOT_BYTES + 1)
    if len(raw) > MAX_SCREENSHOT_BYTES:
        raise ValueError("Screenshot must be 1 MB or smaller.")
    mime = upload.mimetype
    type_info = SCREENSHOT_TYPES.get(mime)
    if not type_info:
        raise ValueError("Screenshot must be a PNG, JPEG, GIF, or WebP image.")
    extension, signature = type_info
    if not raw.startswith(signature) or (mime == "image/webp" and raw[8:12] != b"WEBP"):
        raise ValueError("Screenshot content does not match its image type.")
    storage_name = f"{uuid4().hex}.{extension}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / storage_name).write_bytes(raw)
    original_name = secure_filename(upload.filename) or f"screenshot.{extension}"
    return {"storageName": storage_name, "originalName": original_name[:120], "mime": mime, "size": len(raw)}


def delete_screenshot(submission):
    screenshot = submission.get("screenshot") if submission else None
    if screenshot and screenshot.get("storageName"):
        (UPLOAD_DIR / screenshot["storageName"]).unlink(missing_ok=True)


def admin_submission_payload(submission):
    payload = {key: value for key, value in submission.items() if key != "email"}
    if submission.get("email"):
        payload["email"] = submission["email"]
    if submission.get("screenshot"):
        payload["screenshot"] = {
            key: submission["screenshot"][key]
            for key in ("originalName", "mime", "size")
        }
        payload["screenshot"]["url"] = url_for("api_admin_screenshot", submission_id=submission["id"])
    return payload


def public_payload():
    raised = total_raised()
    goal = float(campaign["goal"])
    return {
        "campaign": campaign,
        "donations": verified_donations,
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
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    return response


@app.template_filter("currency")
def currency(value):
    return money(value)


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
    return jsonify(public_payload())


@app.route("/api/submissions", methods=["POST", "OPTIONS"])
def api_submit_donation():
    if request.method == "OPTIONS":
        return ("", 204)
    if not allow_submission(request.remote_addr or "unknown"):
        return jsonify({"error": "Too many submissions. Please try again later."}), 429
    if campaign_status() != "active":
        return jsonify({"error": "This fundraiser is no longer accepting submissions."}), 409
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    if data.get("honeypot"):
        return jsonify({"error": "Submission rejected."}), 400
    name = str(data.get("name") or "Anonymous").strip()[:80] or "Anonymous"
    email = str(data.get("email") or "").strip()[:160]
    donation_type = data.get("type", "cash")
    submission = {"id": f"submission-{len(pending_submissions) + 1}", "name": name, "email": email, "type": donation_type, "date": datetime.today().strftime("%Y-%m-%d")}
    if donation_type == "cash":
        amount = positive_float(data.get("amount"), 0)
        if amount <= 0:
            return jsonify({"error": "Enter a valid cash amount greater than zero."}), 400
        submission.update({"value": amount, "amount": amount})
    elif donation_type == "goods":
        item = get_item(data.get("itemId") or data.get("item_id"))
        quantity = positive_int(data.get("quantity"), 0)
        if not item or quantity <= 0:
            return jsonify({"error": "Choose a valid item and quantity."}), 400
        submission.update({"item_id": item["id"], "item_name": item["name"], "quantity": quantity, "value": item["value"] * quantity})
    else:
        return jsonify({"error": "Choose a supported donation type."}), 400
    try:
        screenshot = save_screenshot(request.files.get("screenshot"))
        if not screenshot:
            raise ValueError("A payment screenshot is required for every donation.")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    if screenshot:
        submission["screenshot"] = screenshot
    pending_submissions.insert(0, submission)
    persist_state()
    return jsonify({"message": "Thank you. Your donation is pending review."}), 201


@app.route("/api/admin/login", methods=["POST", "OPTIONS"])
def api_admin_login():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    if data.get("password", "") != os.environ.get("ADMIN_PASSWORD", "admin123"):
        return jsonify({"error": "Incorrect password."}), 401
    session["admin_logged_in"] = True
    return jsonify({"authenticated": True})


@app.route("/api/admin/review", methods=["GET"])
def api_admin_review():
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"pending": [admin_submission_payload(entry) for entry in pending_submissions], "verified": verified_donations})


@app.route("/api/admin/export.csv")
def api_admin_export():
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "name", "type", "value", "item", "quantity", "date"])
    for donation in verified_donations:
        writer.writerow([
            donation.get("id", ""), donation.get("name", ""), donation.get("type", ""),
            donation.get("value", ""), donation.get("item_name", ""),
            donation.get("quantity", ""), donation.get("date", ""),
        ])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=verified-donations.csv"
    return response


@app.route("/api/admin/submissions/<submission_id>/screenshot")
def api_admin_screenshot(submission_id):
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    submission = next((entry for entry in pending_submissions if entry["id"] == submission_id), None)
    if not submission or not submission.get("screenshot"):
        return jsonify({"error": "Screenshot not found."}), 404
    screenshot_path = UPLOAD_DIR / submission["screenshot"]["storageName"]
    if not screenshot_path.is_file():
        return jsonify({"error": "Screenshot not found."}), 404
    return send_file(screenshot_path, mimetype=submission["screenshot"]["mime"], as_attachment=False, download_name=submission["screenshot"]["originalName"])


@app.route("/api/admin/submissions/<submission_id>/<action>", methods=["POST"])
def api_admin_moderate(submission_id, action):
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    submission = next((entry for entry in pending_submissions if entry["id"] == submission_id), None)
    if action not in {"approve", "reject"}:
        return jsonify({"error": "Unsupported moderation action."}), 400
    if not submission and submission_id in moderation_log:
        return jsonify(public_payload())
    if not submission:
        return jsonify({"error": "Submission not found."}), 404
    if action == "approve":
        verified_donations.insert(0, {key: value for key, value in submission.items() if key != "email"})
        delete_screenshot(submission)
        verified_donations[0].pop("screenshot", None)
    else:
        delete_screenshot(submission)
    moderation_log[submission_id] = action + "d"
    pending_submissions.remove(submission)
    persist_state()
    if action == "approve":
        thank_donor(submission)
    return jsonify(public_payload())


@app.route("/api/admin/settings", methods=["GET", "PUT"])
def api_admin_settings():
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    if request.method == "GET":
        return jsonify({"campaign": campaign})
    data = request.get_json(silent=True) or {}
    campaign["goal"] = positive_float(data.get("goal"), campaign["goal"])
    campaign["cashtag"] = str(data.get("cashtag") or campaign["cashtag"]).strip()
    campaign["end_date"] = str(data.get("endDate", campaign["end_date"]))
    campaign["distribution"] = str(data.get("distribution") or campaign["distribution"]).strip()
    persist_state()
    return jsonify({"campaign": campaign})


@app.route("/")
def dashboard():
    if (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    raised = total_raised()
    goal = float(campaign["goal"])
    return render_template(
        "index.html", campaign=campaign, donations=verified_donations,
        total_raised=raised, progress=min((raised / goal) * 100, 100) if goal else 0,
        remaining=max(goal - raised, 0), donor_count=len(verified_donations),
        item_totals=item_totals(), admin_session=admin_required(),
    )


@app.route("/assets/<path:filename>")
def frontend_asset(filename):
    if FRONTEND_DIST.exists():
        return send_from_directory(FRONTEND_DIST / "assets", filename)
    return ("", 404)


@app.route("/submissions", methods=["POST"])
def submit_donation():
    if request.form.get("honeypot"):
        flash("Submission rejected.", "error")
        return redirect(url_for("dashboard"))
    if campaign_status() != "active":
        flash("This fundraiser is no longer accepting submissions.", "error")
        return redirect(url_for("dashboard"))
    name = (request.form.get("name") or "Anonymous").strip()[:80] or "Anonymous"
    email = (request.form.get("email") or "").strip()[:160]
    donation_type = request.form.get("type", "cash")
    submission = {"id": f"submission-{len(pending_submissions) + 1}", "name": name, "email": email, "type": donation_type, "date": datetime.today().strftime("%Y-%m-%d")}

    if donation_type == "cash":
        try:
            amount = float(request.form.get("amount", "0"))
        except (TypeError, ValueError):
            amount = 0
        if amount <= 0:
            flash("Enter a valid cash amount greater than zero.", "error")
            return redirect(url_for("dashboard"))
        submission.update({"value": amount, "amount": amount})
    elif donation_type == "goods":
        item = get_item(request.form.get("item_id"))
        quantity = positive_int(request.form.get("quantity"), 0)
        if not item or quantity <= 0:
            flash("Choose a valid item and quantity.", "error")
            return redirect(url_for("dashboard"))
        submission.update({"item_id": item["id"], "item_name": item["name"], "quantity": quantity, "value": item["value"] * quantity})
    else:
        flash("Choose a supported donation type.", "error")
        return redirect(url_for("dashboard"))

    try:
        screenshot = save_screenshot(request.files.get("screenshot"))
        if not screenshot:
            raise ValueError("A payment screenshot is required for every donation.")
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("dashboard"))
    if screenshot:
        submission["screenshot"] = screenshot
    pending_submissions.insert(0, submission)
    persist_state()
    flash("Thank you. Your donation is pending review.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password", "") == os.environ.get("ADMIN_PASSWORD", "admin123"):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect password.", "error")
    return render_template("admin_login.html", campaign=campaign)


@app.route("/admin")
def admin_dashboard():
    if not admin_required():
        return redirect(url_for("admin_login"))
    return render_template("admin.html", campaign=campaign, pending_submissions=pending_submissions, verified_donations=verified_donations)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("dashboard"))


@app.route("/admin/approve/<submission_id>", methods=["POST"])
def approve_submission(submission_id):
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    submission = next((entry for entry in pending_submissions if entry["id"] == submission_id), None)
    if not submission:
        if submission_id in moderation_log:
            return redirect(url_for("admin_dashboard"))
        flash("Submission not found.", "error")
        return redirect(url_for("admin_dashboard"))
    verified_donations.insert(0, {key: value for key, value in submission.items() if key not in {"email", "screenshot"}})
    delete_screenshot(submission)
    moderation_log[submission_id] = "approved"
    pending_submissions.remove(submission)
    persist_state()
    thank_donor(submission)
    flash("Donation approved and added to public totals.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reject/<submission_id>", methods=["POST"])
def reject_submission(submission_id):
    if not admin_required():
        return jsonify({"error": "unauthorized"}), 401
    if submission_id in moderation_log:
        return redirect(url_for("admin_dashboard"))
    submission = next((entry for entry in pending_submissions if entry["id"] == submission_id), None)
    if not submission:
        flash("Submission not found.", "error")
        return redirect(url_for("admin_dashboard"))
    delete_screenshot(submission)
    pending_submissions[:] = [entry for entry in pending_submissions if entry["id"] != submission_id]
    moderation_log[submission_id] = "rejected"
    persist_state()
    flash("Submission rejected.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if not admin_required():
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        campaign["goal"] = positive_float(request.form.get("goal"), campaign["goal"])
        campaign["cashtag"] = (request.form.get("cashtag") or campaign["cashtag"]).strip()
        campaign["end_date"] = request.form.get("end_date", campaign["end_date"])
        campaign["distribution"] = (request.form.get("distribution") or campaign["distribution"]).strip()
        campaign["items"] = [{
            "id": item["id"], "name": item["name"],
            "value": positive_float(request.form.get(f"item_value_{item['id']}"), item["value"]),
            "target": positive_int(request.form.get(f"item_target_{item['id']}"), item["target"]),
        } for item in DEFAULT_ITEMS]
        persist_state()
        flash("Campaign settings saved.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_settings.html", campaign=campaign)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)
