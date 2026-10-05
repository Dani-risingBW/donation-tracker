from app import app


def test_public_page_loads():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "25:35" in text
    assert "Give now" in text or "Give with Cash App" in text


def test_cash_submission_creates_pending_record():
    client = app.test_client()
    response = client.post(
        "/submissions",
        data={
            "type": "cash",
            "amount": "35.00",
            "name": "Test Donor",
            "email": "test@example.com",
            "photo": "",
            "honeypot": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "pending review" in text.lower()


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
