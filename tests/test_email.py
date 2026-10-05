from io import BytesIO

import pytest

import mailer
from test_api import PNG, client, csrf_headers


@pytest.fixture
def mail_env(monkeypatch):
    monkeypatch.setenv("MAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "app-password")
    monkeypatch.setenv("MAIL_SENDER_NAME", "Spread 25:35")
    monkeypatch.setenv("VOLUNTEER_FORM_URL", "https://example.com/volunteer")


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(mailer, "send_thank_you", lambda donation, recipient, raised, goal: calls.append((donation, recipient, raised, goal)))
    return calls


def submit_and_approve(client, email, **fields):
    data = {"type": "cash", "amount": "10", "name": "Test Donor", "email": email, "screenshot": (BytesIO(PNG), "receipt.png"), **fields}
    client.post("/api/submissions", data=data, content_type="multipart/form-data", headers=csrf_headers(client))
    headers = csrf_headers(client)
    client.post("/api/admin/login", json={"password": "admin123"}, headers=headers)
    submission_id = client.get("/api/admin/review").get_json()["pending"][0]["id"]
    return client.post(f"/api/admin/submissions/{submission_id}/approve", headers=headers)


def test_cash_email_names_donor_gift_progress_and_volunteer_link(mail_env):
    message = mailer.compose_thank_you({"name": "Malachi", "type": "cash", "value": 10.0}, "donor@example.com", 450, 1000)
    body = message.get_content()
    assert message["From"] == '"Spread 25:35" <sender@example.com>'
    assert message["To"] == "donor@example.com"
    assert message["Subject"] == "Thank you for partnering with 25:35"
    assert body.startswith("Hi Malachi,")
    assert "Your gift of $10 will go directly" in body
    assert "we've raised $450 of our $1,000 goal, with just $550 to go!" in body
    assert "sign up here: https://example.com/volunteer" in body


def test_goods_email_describes_items_and_anonymous_donors_get_friend(mail_env):
    donation = {"name": "Anonymous", "type": "goods", "item_name": "Bottled Water", "quantity": 10, "value": 10.0}
    body = mailer.compose_thank_you(donation, "donor@example.com", 1200, 1000).get_content()
    assert body.startswith("Hi friend,")
    assert "Your gift of 10 Bottled Water will go directly" in body
    assert "we've reached our $1,000 goal!" in body


def test_email_skips_volunteer_paragraph_without_link(mail_env, monkeypatch):
    monkeypatch.setenv("VOLUNTEER_FORM_URL", "")
    body = mailer.compose_thank_you({"name": "A", "type": "cash", "value": 5.5}, "donor@example.com", 5.5, 1000).get_content()
    assert "$5.50" in body
    assert "sign up" not in body


def test_send_is_skipped_without_credentials_or_address(monkeypatch):
    monkeypatch.delenv("MAIL_USERNAME", raising=False)
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    donation = {"name": "A", "type": "cash", "value": 5.0}
    assert mailer.send_thank_you(donation, "donor@example.com", 5, 1000) is False
    monkeypatch.setenv("MAIL_USERNAME", "sender@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "app-password")
    assert mailer.send_thank_you(donation, "", 5, 1000) is False
    assert mailer.send_thank_you(donation, "not-an-email", 5, 1000) is False


def test_approval_emails_donor_with_updated_total(client, sent):
    before = client.get("/api/campaign").get_json()["totalRaised"]
    assert submit_and_approve(client, "donor@example.com").status_code == 200
    assert len(sent) == 1
    donation, recipient, raised, goal = sent[0]
    assert recipient == "donor@example.com"
    assert donation["value"] == 10.0
    assert raised == before + 10.0


class InlineThread:
    def __init__(self, target, args, daemon):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


def test_only_approvals_with_an_email_reach_gmail(client, mail_env, monkeypatch):
    delivered = []
    monkeypatch.setattr(mailer, "send_message", delivered.append)
    monkeypatch.setattr(mailer.threading, "Thread", InlineThread)
    submit_and_approve(client, "")
    assert delivered == []
    client.post("/api/submissions", data={"type": "cash", "amount": "5", "email": "donor@example.com", "screenshot": (BytesIO(PNG), "r.png")}, content_type="multipart/form-data", headers=csrf_headers(client))
    submission_id = client.get("/api/admin/review").get_json()["pending"][0]["id"]
    client.post(f"/api/admin/submissions/{submission_id}/reject", headers=csrf_headers(client))
    assert delivered == []
    submit_and_approve(client, "donor@example.com")
    assert [message["To"] for message in delivered] == ["donor@example.com"]


def test_approved_record_does_not_store_donor_email(client, sent):
    submit_and_approve(client, "donor@example.com")
    assert "email" not in client.get("/api/admin/review").get_json()["verified"][0]
