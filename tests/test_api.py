import copy
from io import BytesIO

import pytest

import app as app_module
from app import app, campaign, moderation_log, pending_submissions, persist_state, verified_donations

PNG = b"\x89PNG\r\n\x1a\n" + b"test image bytes"


def csrf_headers(client):
    return {"X-CSRF-Token": client.get("/api/csrf").get_json()["token"]}


@pytest.fixture
def client():
    original_campaign = copy.deepcopy(campaign)
    original_verified = copy.deepcopy(verified_donations)
    original_pending = copy.deepcopy(pending_submissions)
    original_log = copy.deepcopy(moderation_log)
    original_upload_dir = app_module.UPLOAD_DIR
    original_attempts = copy.deepcopy(app_module.submission_attempts)
    pending_submissions.clear()
    moderation_log.clear()
    app_module.submission_attempts.clear()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client
    campaign.clear()
    campaign.update(original_campaign)
    verified_donations[:] = original_verified
    pending_submissions[:] = original_pending
    moderation_log.clear()
    moderation_log.update(original_log)
    app_module.UPLOAD_DIR = original_upload_dir
    app_module.submission_attempts.clear()
    app_module.submission_attempts.update(original_attempts)
    persist_state()


def test_public_campaign_excludes_pending_donations(client):
    before = client.get("/api/campaign").get_json()["totalRaised"]
    response = client.post(
        "/api/submissions",
        data={"type": "cash", "amount": "50", "name": "Pending Donor", "screenshot": (BytesIO(PNG), "receipt.png")},
        content_type="multipart/form-data",
        headers=csrf_headers(client),
    )
    assert response.status_code == 201
    assert client.get("/api/campaign").get_json()["totalRaised"] == before


def test_admin_can_approve_once_and_retry_safely(client):
    client.post(
        "/api/submissions",
        data={"type": "goods", "itemId": "water", "quantity": "3", "screenshot": (BytesIO(PNG), "receipt.png")},
        content_type="multipart/form-data",
        headers=csrf_headers(client),
    )
    assert client.post("/api/admin/login", json={"password": "admin123"}, headers=csrf_headers(client)).status_code == 200
    submission_id = client.get("/api/admin/review").get_json()["pending"][0]["id"]

    first = client.post(f"/api/admin/submissions/{submission_id}/approve", headers=csrf_headers(client))
    second = client.post(f"/api/admin/submissions/{submission_id}/approve", headers=csrf_headers(client))

    assert first.status_code == 200
    assert second.status_code == 200
    assert len([donation for donation in verified_donations if donation["id"] == submission_id]) == 1


def test_admin_api_requires_authentication(client):
    assert client.get("/api/admin/review").status_code == 401
    assert client.post("/api/admin/submissions/missing/approve", headers=csrf_headers(client)).status_code == 401


def test_api_mutations_require_csrf(client):
    assert client.post("/api/admin/login", json={"password": "admin123"}).status_code == 403


def test_submission_rate_limit_is_enforced(client, monkeypatch):
    monkeypatch.setenv("SUBMISSION_RATE_LIMIT", "1")
    headers = csrf_headers(client)
    data = {"type": "cash", "amount": "25", "screenshot": (BytesIO(PNG), "receipt.png")}
    assert client.post("/api/submissions", data=data, content_type="multipart/form-data", headers=headers).status_code == 201
    second = client.post("/api/submissions", data={"type": "cash", "amount": "25", "screenshot": (BytesIO(PNG), "receipt.png")}, content_type="multipart/form-data", headers=headers)
    assert second.status_code == 429


def test_admin_can_export_verified_csv(client):
    assert client.get("/api/admin/export.csv").status_code == 401
    client.post("/api/admin/login", json={"password": "admin123"}, headers=csrf_headers(client))
    response = client.get("/api/admin/export.csv")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "id,name,type,value,item,quantity,date" in body
    assert "Amina O." in body


def test_admin_can_update_campaign_settings(client):
    headers = csrf_headers(client)
    assert client.post("/api/admin/login", json={"password": "admin123"}, headers=headers).status_code == 200
    response = client.put(
        "/api/admin/settings",
        json={"goal": 2500, "cashtag": "$UpdatedTag", "endDate": "2030-01-01", "distribution": "Updated details"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json()["campaign"]["goal"] == 2500
    assert response.get_json()["campaign"]["cashtag"] == "$UpdatedTag"


def test_screenshot_is_private_and_cleaned_after_approval(client, tmp_path):
    app_module.UPLOAD_DIR = tmp_path
    image = b"\x89PNG\r\n\x1a\n" + b"test image bytes"
    response = client.post(
        "/api/submissions",
        data={"type": "cash", "amount": "25", "screenshot": (BytesIO(image), "receipt.png")},
        content_type="multipart/form-data",
        headers=csrf_headers(client),
    )
    assert response.status_code == 201
    submission_id = pending_submissions[0]["id"]
    stored_path = tmp_path / pending_submissions[0]["screenshot"]["storageName"]
    assert stored_path.is_file()

    assert client.get(f"/api/admin/submissions/{submission_id}/screenshot").status_code == 401
    client.post("/api/admin/login", json={"password": "admin123"}, headers=csrf_headers(client))
    review = client.get("/api/admin/review").get_json()
    assert review["pending"][0]["screenshot"]["originalName"] == "receipt.png"
    assert client.get(f"/api/admin/submissions/{submission_id}/screenshot").status_code == 200
    assert client.post(f"/api/admin/submissions/{submission_id}/approve", headers=csrf_headers(client)).status_code == 200
    assert not stored_path.exists()


def test_submission_without_screenshot_is_rejected(client):
    response = client.post("/api/submissions", json={"type": "cash", "amount": 25}, headers=csrf_headers(client))
    assert response.status_code == 400
    assert "screenshot is required" in response.get_json()["error"].lower()


def test_ended_campaign_rejects_new_submissions(client):
    campaign["end_date"] = "2000-01-01"
    response = client.post(
        "/api/submissions",
        json={"type": "cash", "amount": 25},
        headers=csrf_headers(client),
    )
    assert response.status_code == 409
    assert "no longer accepting" in response.get_json()["error"].lower()