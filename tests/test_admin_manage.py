"""Admin 采集管理 API 测试。"""

import pytest

from wechat_collector.config import get_settings

AUTH_HEADERS = {"X-API-Token": "test-token"}


@pytest.fixture
def api_client(db_session, monkeypatch):
    from fastapi.testclient import TestClient

    from wechat_collector.api.app import app
    from wechat_collector.db.base import get_db

    get_settings.cache_clear()
    monkeypatch.setenv("COLLECTOR_API_TOKEN", "test-token")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_pilot_accounts_crud(api_client, db_session) -> None:
    create = api_client.post(
        "/admin/pilot-accounts",
        json={
            "org_code": "wc_test",
            "org_name": "测试组织",
            "account_name": "测试公众号",
            "aliases": "别名A",
            "priority": "high",
        },
        headers=AUTH_HEADERS,
    )
    assert create.status_code == 201
    row = create.json()
    assert row["org_code"] == "wc_test"
    assert row["account_name"] == "测试公众号"

    listing = api_client.get("/admin/pilot-accounts", headers=AUTH_HEADERS)
    assert listing.status_code == 200
    assert any(item["account_id"] == row["account_id"] for item in listing.json())

    update = api_client.put(
        f"/admin/pilot-accounts/{row['account_id']}",
        json={"org_name": "测试组织（改）", "account_name": "测试公众号（改）"},
        headers=AUTH_HEADERS,
    )
    assert update.status_code == 200
    assert update.json()["org_name"] == "测试组织(改)"

    delete = api_client.delete(
        f"/admin/pilot-accounts/{row['account_id']}",
        headers=AUTH_HEADERS,
    )
    assert delete.status_code == 204


def test_admin_settings_list(api_client) -> None:
    resp = api_client.get("/admin/settings", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    keys = {item["key"] for item in items}
    assert "COLLECTOR_API_TOKEN" in keys
    token_item = next(i for i in items if i["key"] == "COLLECTOR_API_TOKEN")
    assert "•" in str(token_item["value"])


def test_admin_manage_page(api_client) -> None:
    resp = api_client.get("/admin/manage")
    assert resp.status_code == 200
    assert "采集管理" in resp.text
