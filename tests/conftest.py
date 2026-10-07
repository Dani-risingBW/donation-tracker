import copy
import os
import tempfile

# Point the app at a throwaway database before backend.app is imported, so tests never touch instance/.
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(prefix="donation-tracker-tests-"), "test.sqlite3")

import pytest  # noqa: E402

import backend.app as app_module  # noqa: E402
from backend import mailer  # noqa: E402
from backend.app import app, campaign, moderation_log, pending_submissions, persist_state, verified_donations  # noqa: E402


@pytest.fixture(autouse=True)
def no_real_email(monkeypatch):
    """Tests must never reach Gmail, even if MAIL_* settings are present."""
    def refuse(message):
        raise AssertionError("Tests attempted to send a real email.")
    monkeypatch.setattr(mailer, "send_message", refuse)


def csrf_headers(client):
    return {"X-CSRF-Token": client.get("/api/csrf").get_json()["token"]}


@pytest.fixture
def client():
    original_campaign = copy.deepcopy(campaign)
    original_verified = copy.deepcopy(verified_donations)
    original_pending = copy.deepcopy(pending_submissions)
    original_log = copy.deepcopy(moderation_log)
    pending_submissions.clear()
    moderation_log.clear()
    app_module.rate_limit_attempts.clear()
    campaign["end_date"] = ""  # keep tests independent of the real closing date
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client
    campaign.clear()
    campaign.update(original_campaign)
    verified_donations[:] = original_verified
    pending_submissions[:] = original_pending
    moderation_log.clear()
    moderation_log.update(original_log)
    app_module.rate_limit_attempts.clear()
    persist_state()


def login(client):
    return client.post("/api/admin/login", json={"password": "admin123"}, headers=csrf_headers(client))


def submit_goods(client, **fields):
    data = {"type": "goods", "itemId": "sandwiches", "quantity": 3, **fields}
    return client.post("/api/submissions", json=data, headers=csrf_headers(client))
