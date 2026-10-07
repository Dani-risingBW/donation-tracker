import importlib
import sys

import pytest


def test_public_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.get_data(as_text=True)
    campaign = client.get("/api/campaign")
    assert campaign.status_code == 200
    assert campaign.get_json()["campaign"]["name"] == "25:35"


def test_admin_page_is_served_by_react(client):
    response = client.get("/admin")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.get_data(as_text=True)


def test_legacy_form_routes_are_gone(client):
    assert client.post("/submissions").status_code in {404, 405}
    assert client.post("/admin/login").status_code in {404, 405}
    assert client.post("/admin/approve/anything").status_code == 404


def test_campaign_starts_with_launch_defaults(client):
    data = client.get("/api/campaign").get_json()
    assert data["campaign"]["goal"] == 2000.0
    assert data["campaign"]["gofundme_url"] == "https://gofund.me/901ac545b"
    assert data["donations"] == []
    assert data["totalRaised"] == 0


@pytest.mark.parametrize("missing", ["SECRET_KEY", "ADMIN_PASSWORD"])
def test_production_entry_point_requires_real_secrets(monkeypatch, missing):
    monkeypatch.setenv("SECRET_KEY", "a-real-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-real-password")
    monkeypatch.delenv(missing)
    sys.modules.pop("backend.wsgi", None)
    with pytest.raises(RuntimeError, match=missing):
        importlib.import_module("backend.wsgi")


def test_production_entry_point_rejects_development_password(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-real-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    sys.modules.pop("backend.wsgi", None)
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        importlib.import_module("backend.wsgi")


def test_production_entry_point_starts_with_real_secrets(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-real-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-real-password")
    sys.modules.pop("backend.wsgi", None)
    assert importlib.import_module("backend.wsgi").app.name == "backend.app"
