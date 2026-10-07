import backend.app as app_module
from backend.app import campaign, pending_submissions, verified_donations
from conftest import csrf_headers, login, submit_goods


def test_public_campaign_excludes_pending_donations(client):
    before = client.get("/api/campaign").get_json()["totalRaised"]
    assert submit_goods(client, name="Pending Donor").status_code == 201
    assert client.get("/api/campaign").get_json()["totalRaised"] == before


def test_public_form_rejects_cash(client):
    response = client.post("/api/submissions", json={"type": "cash", "amount": 25}, headers=csrf_headers(client))
    assert response.status_code == 400
    assert "gofundme" in response.get_json()["error"].lower()
    assert pending_submissions == []


def test_goods_submission_validates_item_and_quantity(client):
    assert submit_goods(client, itemId="not-an-item").status_code == 400
    assert submit_goods(client, quantity=0).status_code == 400
    assert submit_goods(client, email="not-an-email").status_code == 400
    assert pending_submissions == []


def test_submission_ids_are_unique_after_moderation(client):
    login(client)
    seen = set()
    for _ in range(3):
        submit_goods(client)
        submission_id = pending_submissions[0]["id"]
        assert submission_id not in seen
        seen.add(submission_id)
        client.post(f"/api/admin/submissions/{submission_id}/approve", headers=csrf_headers(client))
    assert len({donation["id"] for donation in verified_donations}) == len(verified_donations)


def test_admin_can_approve_once_and_retry_safely(client):
    submit_goods(client)
    assert login(client).status_code == 200
    submission_id = client.get("/api/admin/review").get_json()["pending"][0]["id"]

    first = client.post(f"/api/admin/submissions/{submission_id}/approve", headers=csrf_headers(client))
    second = client.post(f"/api/admin/submissions/{submission_id}/approve", headers=csrf_headers(client))

    assert first.status_code == 200
    assert second.status_code == 200
    assert len([donation for donation in verified_donations if donation["id"] == submission_id]) == 1


def test_admin_api_requires_authentication(client):
    assert client.get("/api/admin/review").status_code == 401
    assert client.post("/api/admin/submissions/missing/approve", headers=csrf_headers(client)).status_code == 401


def test_admin_can_log_out(client):
    login(client)
    assert client.get("/api/admin/review").status_code == 200
    assert client.post("/api/admin/logout", headers=csrf_headers(client)).status_code == 200
    assert client.get("/api/admin/review").status_code == 401


def test_api_mutations_require_csrf(client):
    assert client.post("/api/admin/login", json={"password": "admin123"}).status_code == 403


def test_submission_rate_limit_is_enforced(client, monkeypatch):
    monkeypatch.setenv("SUBMISSION_RATE_LIMIT", "1")
    assert submit_goods(client).status_code == 201
    assert submit_goods(client).status_code == 429


def test_rate_limit_is_per_visitor_behind_proxy(client, monkeypatch):
    monkeypatch.setenv("SUBMISSION_RATE_LIMIT", "1")
    headers = csrf_headers(client)
    first = {**headers, "X-Forwarded-For": "203.0.113.1"}
    second = {**headers, "X-Forwarded-For": "203.0.113.2"}
    data = {"type": "goods", "itemId": "sandwiches", "quantity": 1}
    assert client.post("/api/submissions", json=data, headers=first).status_code == 201
    assert client.post("/api/submissions", json=data, headers=first).status_code == 429
    assert client.post("/api/submissions", json=data, headers=second).status_code == 201


def test_admin_login_attempts_are_limited(client):
    headers = csrf_headers(client)
    for _ in range(5):
        assert client.post("/api/admin/login", json={"password": "wrong"}, headers=headers).status_code == 401
    assert client.post("/api/admin/login", json={"password": "admin123"}, headers=headers).status_code == 429


def test_public_payload_never_includes_donor_email(client):
    submit_goods(client, email="donor@example.com")
    login(client)
    submission_id = pending_submissions[0]["id"]
    client.post(f"/api/admin/submissions/{submission_id}/approve", headers=csrf_headers(client))
    assert verified_donations[0]["email"] == "donor@example.com"
    assert "donor@example.com" not in client.get("/api/campaign").get_data(as_text=True)


def test_admin_can_export_verified_csv_with_emails(client):
    assert client.get("/api/admin/export.csv").status_code == 401
    login(client)
    client.post("/api/admin/donations", json={"type": "cash", "name": "GoFundMe donor", "value": 40, "email": "gfm@example.com"}, headers=csrf_headers(client))
    response = client.get("/api/admin/export.csv")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "id,name,email,type,value,item,quantity,date" in body
    assert "GoFundMe donor,gfm@example.com,cash,40.0" in body


def test_admin_can_update_campaign_settings(client):
    headers = csrf_headers(client)
    assert login(client).status_code == 200
    response = client.put(
        "/api/admin/settings",
        json={"goal": 2500, "cashtag": "$UpdatedTag", "endDate": "2030-01-01", "distribution": "Updated details", "gofundmeUrl": "https://gofund.me/new"},
        headers=headers,
    )
    assert response.status_code == 200
    updated = response.get_json()["campaign"]
    assert updated["goal"] == 2500
    assert updated["cashtag"] == "$UpdatedTag"
    assert updated["gofundme_url"] == "https://gofund.me/new"


def test_settings_reject_unsafe_gofundme_link_and_bad_date(client):
    headers = csrf_headers(client)
    login(client)
    assert client.put("/api/admin/settings", json={"gofundmeUrl": "javascript:alert(1)"}, headers=headers).status_code == 400
    assert client.put("/api/admin/settings", json={"endDate": "soon"}, headers=headers).status_code == 400
    assert campaign["gofundme_url"] == "https://gofund.me/901ac545b"


def test_admin_can_create_update_and_delete_manual_donation(client):
    headers = csrf_headers(client)
    assert login(client).status_code == 200
    created = client.post(
        "/api/admin/donations",
        json={"type": "cash", "name": "Manual Donor", "value": 40, "email": "manual@example.com"},
        headers=headers,
    )
    assert created.status_code == 201
    donation_id = next(entry["id"] for entry in verified_donations if entry["name"] == "Manual Donor")

    updated = client.put(
        f"/api/admin/donations/{donation_id}",
        json={"type": "cash", "name": "Updated Donor", "value": 55},
        headers=headers,
    )
    assert updated.status_code == 200
    assert any(entry["id"] == donation_id and entry["value"] == 55 and entry["email"] == "manual@example.com" for entry in verified_donations)

    deleted = client.delete(f"/api/admin/donations/{donation_id}", headers=headers)
    assert deleted.status_code == 200
    assert all(entry["id"] != donation_id for entry in verified_donations)


def test_admin_can_update_item_progress_settings(client):
    headers = csrf_headers(client)
    assert login(client).status_code == 200
    items = client.get("/api/admin/settings").get_json()["campaign"]["items"]
    items[0]["value"] = 12
    items[0]["target"] = 75
    response = client.put("/api/admin/settings", json={"items": items}, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["campaign"]["items"][0]["value"] == 12
    assert response.get_json()["campaign"]["items"][0]["target"] == 75


def test_item_values_and_targets_must_be_whole_numbers(client):
    headers = csrf_headers(client)
    assert login(client).status_code == 200
    items = client.get("/api/admin/settings").get_json()["campaign"]["items"]
    items[0]["value"] = "8"
    items[0]["target"] = 75
    assert client.put("/api/admin/settings", json={"items": items}, headers=headers).status_code == 200
    assert campaign["items"][0]["value"] == 8
    for field, bad in (("value", 8.01), ("target", "7.5")):
        changed = [dict(item) for item in items]
        changed[0][field] = bad
        response = client.put("/api/admin/settings", json={"items": changed}, headers=headers)
        assert response.status_code == 400
        assert "whole numbers" in response.get_json()["error"]


def test_goods_quantity_must_be_a_whole_number(client):
    assert submit_goods(client, quantity=2.5).status_code == 400
    assert submit_goods(client, quantity="2").status_code == 201


def test_saved_placeholder_items_are_replaced_with_care_packages():
    saved = {"items": [{"id": item_id} for item_id in app_module.PLACEHOLDER_ITEM_IDS]}
    assert app_module.replace_placeholder_items(saved)
    assert [item["id"] for item in saved["items"]] == [item["id"] for item in app_module.DEFAULT_ITEMS]
    assert not app_module.replace_placeholder_items(saved)


def test_ended_campaign_rejects_new_submissions(client):
    campaign["end_date"] = "2000-01-01"
    response = submit_goods(client)
    assert response.status_code == 409
    assert "no longer accepting" in response.get_json()["error"].lower()
