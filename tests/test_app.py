from io import BytesIO

from backend.app import app, pending_submissions


def test_public_page_loads():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "25:35" in text
    assert '<div id="root"></div>' in text
    campaign = client.get("/api/campaign")
    assert campaign.status_code == 200
    assert campaign.get_json()["campaign"]["name"] == "25:35"


def test_cash_submission_creates_pending_record():
    client = app.test_client()
    response = client.post(
        "/submissions",
        data={
            "type": "cash",
            "amount": "35.00",
            "name": "Test Donor",
            "email": "test@example.com",
            "screenshot": (BytesIO(b"\x89PNG\r\n\x1a\n"), "payment.png"),
            "honeypot": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert any(
        submission["name"] == "Test Donor"
        and submission["value"] == 35.0
        for submission in pending_submissions
    )


def test_admin_requires_authentication():
    client = app.test_client()
    response = client.get("/admin")
    assert response.status_code == 302


def test_admin_login_success():
    client = app.test_client()
    response = client.post(
        "/admin/login",
        data={"password": "admin123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Review queue" in text or "Admin" in text
