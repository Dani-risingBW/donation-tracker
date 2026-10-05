import copy
from io import BytesIO

import pytest

import app as app_module
from app import app, campaign, moderation_log, pending_submissions, persist_state, verified_donations

PNG = b"\x89PNG\r\n\x1a\n" + b"test image bytes"


@pytest.fixture
def client():
    original_campaign = copy.deepcopy(campaign)
    original_verified = copy.deepcopy(verified_donations)
    original_pending = copy.deepcopy(pending_submissions)
    original_log = copy.deepcopy(moderation_log)
    original_upload_dir = app_module.UPLOAD_DIR
    pending_submissions.clear()
    moderation_log.clear()
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
    persist_state()


def test_public_campaign_excludes_pending_donations(client):
    before = client.get("/api/campaign").get_json()["totalRaised"]
    response = client.post(
        "/api/submissions",
        data={"type": "cash", "amount": "50", "name": "Pending Donor", "screenshot": (BytesIO(PNG), "receipt.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert client.get("/api/campaign").get_json()["totalRaised"] == before


def test_admin_can_approve_once_and_retry_safely(client):
    client.post(
        "/api/submissions",
        data={"type": "goods", "itemId": "water", "quantity": "3", "screenshot": (BytesIO(PNG), "receipt.png")},
        content_type="multipart/form-data",
    )
    assert client.post("/api/admin/login", json={"password": "admin123"}).status_code == 200
    submission_id = client.get("/api/admin/review").get_json()["pending"][0]["id"]

    first = client.post(f"/api/admin/submissions/{submission_id}/approve")
    second = client.post(f"/api/admin/submissions/{submission_id}/approve")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len([donation for donation in verified_donations if donation["id"] == submission_id]) == 1


def test_admin_api_requires_authentication(client):
    assert client.get("/api/admin/review").status_code == 401
    assert client.post("/api/admin/submissions/missing/approve").status_code == 401


def test_screenshot_is_private_and_cleaned_after_approval(client, tmp_path):
    app_module.UPLOAD_DIR = tmp_path
    image = b"\x89PNG\r\n\x1a\n" + b"test image bytes"
    response = client.post(
        "/api/submissions",
        data={"type": "cash", "amount": "25", "screenshot": (BytesIO(image), "receipt.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    submission_id = pending_submissions[0]["id"]
    stored_path = tmp_path / pending_submissions[0]["screenshot"]["storageName"]
    assert stored_path.is_file()

    assert client.get(f"/api/admin/submissions/{submission_id}/screenshot").status_code == 401
    client.post("/api/admin/login", json={"password": "admin123"})
    review = client.get("/api/admin/review").get_json()
    assert review["pending"][0]["screenshot"]["originalName"] == "receipt.png"
    assert client.get(f"/api/admin/submissions/{submission_id}/screenshot").status_code == 200
    assert client.post(f"/api/admin/submissions/{submission_id}/approve").status_code == 200
    assert not stored_path.exists()


def test_submission_without_screenshot_is_rejected(client):
    response = client.post("/api/submissions", json={"type": "cash", "amount": 25})
    assert response.status_code == 400
    assert "screenshot is required" in response.get_json()["error"].lower()