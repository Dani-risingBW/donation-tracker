from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-in-production"

campaign = {
    "name": "Community Education Fund",
    "description": "Help provide books, supplies, and learning support for local students.",
    "goal": 10000.00,
}

donations = [
    {"name": "Amina Okafor", "amount": 250.00, "date": "2026-09-28"},
    {"name": "Jordan Lee", "amount": 100.00, "date": "2026-09-26"},
    {"name": "Anonymous", "amount": 75.00, "date": "2026-09-24"},
]


@app.template_filter("currency")
def currency(value):
    return f"${value:,.2f}"


@app.route("/", methods=["GET"])
def dashboard():
    raised = sum(donation["amount"] for donation in donations)
    progress = min((raised / campaign["goal"]) * 100, 100) if campaign["goal"] else 0
    return render_template(
        "index.html",
        campaign=campaign,
        donations=donations,
        raised=raised,
        progress=progress,
        donor_count=len(donations),
    )


@app.route("/donations", methods=["POST"])
def add_donation():
    name = request.form.get("name", "").strip() or "Anonymous"
    try:
        amount = float(request.form.get("amount", "0"))
    except ValueError:
        amount = 0

    if amount <= 0:
        flash("Enter a donation amount greater than zero.", "error")
        return redirect(url_for("dashboard"))

    donations.insert(
        0,
        {"name": name, "amount": amount, "date": datetime.now().strftime("%Y-%m-%d")},
    )
    flash("Donation recorded successfully.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
