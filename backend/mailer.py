import logging
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr


logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SUBJECT = "Thank you for partnering with 25:35"


def mail_settings():
    return {
        "username": os.environ.get("MAIL_USERNAME", ""),
        "password": os.environ.get("MAIL_PASSWORD", ""),
        "sender_name": os.environ.get("MAIL_SENDER_NAME", "Spread 25:35"),
        "volunteer_url": os.environ.get(
            "VOLUNTEER_FORM_URL", "https://docs.google.com/forms/d/e/1FAIpQLSfingNyaQYAfLHCKJTrau8OozUlUEV-haxXMNalJy93zLrbeA/viewform"
        ).strip(),
    }


def is_configured():
    settings = mail_settings()
    return bool(settings["username"] and settings["password"])


def friendly_money(value):
    value = float(value)
    return f"${value:,.0f}" if value.is_integer() else f"${value:,.2f}"


def describe_gift(donation):
    if donation["type"] == "goods":
        return f"{donation['quantity']} {donation['item_name']}"
    return friendly_money(donation["value"])


def progress_line(raised, goal):
    if raised >= goal:
        return f"Thanks to your support, we've reached our {friendly_money(goal)} goal!"
    return (
        f"Thanks to your support, we've raised {friendly_money(raised)} of our "
        f"{friendly_money(goal)} goal, with just {friendly_money(goal - raised)} to go!"
    )


def compose_thank_you(donation, recipient, raised, goal):
    settings = mail_settings()
    name = donation.get("name", "").strip()
    greeting = f"Hi {name}," if name and name != "Anonymous" else "Hi friend,"
    paragraphs = [
        greeting,
        "Thank you so much for partnering with us as we serve our unhoused neighbors in Washington, D.C. "
        f"Your gift of {describe_gift(donation)} will go directly toward meeting their practical needs.",
        progress_line(raised, goal),
    ]
    if settings["volunteer_url"]:
        paragraphs.append(f"If you'd also like to serve alongside us in person, you can sign up here: {settings['volunteer_url']}")
    paragraphs += [
        "We're so glad to have you with us as we serve our community.",
        "With gratitude,\nThe 25:35 Team",
    ]

    message = EmailMessage()
    message["Subject"] = SUBJECT
    message["From"] = formataddr((settings["sender_name"], settings["username"]))
    message["To"] = recipient
    message.set_content("\n\n".join(paragraphs) + "\n")
    return message


def send_message(message):
    settings = mail_settings()
    # An explicit default context makes Python verify Gmail's certificate.
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20, context=ssl.create_default_context()) as server:
        server.login(settings["username"], settings["password"])
        server.send_message(message)


def _send_safely(message):
    try:
        send_message(message)
        logger.info("Sent thank-you email to %s", message["To"])
    except Exception:
        logger.exception("Could not send thank-you email to %s", message["To"])


def send_thank_you(donation, recipient, raised, goal):
    """Email a donor in the background so approving a donation never waits on Gmail."""
    if not recipient or "@" not in recipient:
        return False
    if not is_configured():
        logger.warning("Thank-you email skipped: MAIL_USERNAME and MAIL_PASSWORD are not set.")
        return False
    try:
        message = compose_thank_you(donation, recipient, raised, goal)
    except ValueError:
        logger.warning("Thank-you email skipped: invalid recipient address.")
        return False
    threading.Thread(target=_send_safely, args=(message,), daemon=True).start()
    return True
