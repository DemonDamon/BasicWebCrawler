"""FastAPI 集成测试。"""

import pytest
from fastapi.testclient import TestClient

from wechat_collector.api.app import app
from wechat_collector.config import get_settings
from wechat_collector.db.base import get_db

AUTH_HEADERS = {
    "X-API-Token": "test-token",
    "X-Client-Id": "pytest-client",
    "X-Plugin-Version": "0.1.0",
}


@pytest.fixture
def api_client(db_session, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("COLLECTOR_API_TOKEN", "test-token")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_missing_token_returns_401(api_client) -> None:
    response = api_client.post(
        "/api/articles",
        json={"title": "t", "url": "https://mp.weixin.qq.com/s?__biz=a&mid=1&idx=1"},
    )
    assert response.status_code == 401


def test_ingest_article_deduplicates(api_client) -> None:
    payload = {
        "title": "测试文章",
        "url": "https://mp.weixin.qq.com/s?__biz=dup&mid=1&idx=1",
        "content_text": "相同正文内容用于去重",
        "account_name": "测试号",
    }
    first = api_client.post("/api/articles", json=payload, headers=AUTH_HEADERS)
    second = api_client.post("/api/articles", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert second.json()["duplicate_reason"] == "content_hash"
    assert first.json()["id"] == second.json()["id"]


def test_candidate_and_task_flow(api_client) -> None:
    create_resp = api_client.post(
        "/api/candidates",
        json={
            "url": "https://mp.weixin.qq.com/s?__biz=task&mid=1&idx=1&sn=1",
            "source": "manual",
            "title": "待采集",
        },
        headers=AUTH_HEADERS,
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["created"] is True

    dup_resp = api_client.post(
        "/api/candidates",
        json={
            "url": "https://mp.weixin.qq.com/s?__biz=task&mid=1&idx=1&sn=2",
            "source": "bing_search",
        },
        headers=AUTH_HEADERS,
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json()["created"] is False

    next_resp = api_client.get("/api/crawl/tasks/next", headers=AUTH_HEADERS)
    assert next_resp.status_code == 200
    task = next_resp.json()
    assert task is not None
    assert task["status"] == "processing"

    success_resp = api_client.post(
        f"/api/crawl/tasks/{task['id']}/success",
        headers=AUTH_HEADERS,
    )
    assert success_resp.status_code == 200
    assert success_resp.json()["status"] == "success"


def test_import_candidates_and_coverage(api_client) -> None:
    import_resp = api_client.post(
        "/api/candidates/import",
        json={
            "urls": [
                "https://mp.weixin.qq.com/s?__biz=imp1&mid=1&idx=1",
                "https://mp.weixin.qq.com/s?__biz=imp2&mid=1&idx=1",
                "",
            ],
            "source": "manual",
        },
        headers=AUTH_HEADERS,
    )
    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["created"] == 2
    assert body["skipped"] == 1

    coverage_resp = api_client.get("/api/coverage/report", headers=AUTH_HEADERS)
    assert coverage_resp.status_code == 200
    report = coverage_resp.json()
    assert report["candidate_total"] >= 2
    assert "article_total" in report


def test_admin_list_articles(api_client) -> None:
    api_client.post(
        "/api/articles",
        json={
            "title": "后台列表文章",
            "url": "https://mp.weixin.qq.com/s?__biz=admin&mid=1&idx=1",
            "content_text": "后台可见",
        },
        headers=AUTH_HEADERS,
    )
    response = api_client.get("/admin/articles", headers=AUTH_HEADERS)
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert items[0]["title"]


def test_healthz_without_auth(api_client) -> None:
    assert api_client.get("/healthz").json()["status"] == "ok"
