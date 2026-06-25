from pathlib import Path

from wechat_collector.io.import_orgs import import_orgs_from_csv
from wechat_collector.services import org_service


def test_normalize_aliases_json_and_semicolon() -> None:
    assert org_service.normalize_aliases('["市发改委", "发改局"]') == ["市发改委", "发改局"]
    assert org_service.normalize_aliases("市教育局; 区教育局") == ["市教育局", "区教育局"]


def test_normalize_aliases_fullwidth_and_dedupe() -> None:
    assert org_service.normalize_aliases(["ＡＢＣ", "ABC"]) == ["ABC"]


def test_upsert_organization_idempotent(db_session) -> None:
    first = org_service.upsert_organization_by_code(
        db_session,
        org_code="org_001",
        org_name="示例局",
        aliases='["别名A"]',
        region="示例市",
    )
    second = org_service.upsert_organization_by_code(
        db_session,
        org_code="org_001",
        org_name="示例局（更新）",
        aliases='["别名B"]',
        region="示例市",
    )
    assert first.id == second.id
    assert second.org_name == "示例局(更新)"
    assert org_service.list_organizations(db_session) == [second]


def test_bind_multiple_accounts_for_one_org(db_session) -> None:
    org = org_service.create_organization(
        db_session,
        org_code="org_multi",
        org_name="示例多号组织",
    )
    account_a = org_service.bind_wechat_account(
        db_session,
        org.id,
        account_name="示例发布",
        wechat_id="demo_pub",
    )
    account_b = org_service.bind_wechat_account(
        db_session,
        org.id,
        account_name="示例服务",
        wechat_id="demo_svc",
    )
    accounts = org_service.list_wechat_accounts_for_org(db_session, org.id)
    assert len(accounts) == 2
    assert {item.id for item in accounts} == {account_a.id, account_b.id}


def test_unbind_account(db_session) -> None:
    org = org_service.create_organization(db_session, org_code="org_unbind", org_name="解绑示例")
    account = org_service.bind_wechat_account(db_session, org.id, account_name="示例号")
    org_service.unbind_wechat_account(db_session, account.id)
    refreshed = db_session.get(type(account), account.id)
    assert refreshed is not None
    assert refreshed.org_id is None
    assert refreshed.status == "inactive"


def test_get_search_names(db_session) -> None:
    org = org_service.create_organization(
        db_session,
        org_code="org_search",
        org_name="示例搜索组织",
        aliases='["简称A", "简称B"]',
    )
    names = org_service.get_search_names(org)
    assert names[0] == "示例搜索组织"
    assert "简称A" in names
    assert "简称B" in names


def test_import_orgs_from_csv_idempotent(db_session, tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "orgs.csv"
    csv_path.write_text(
        "org_code,org_name,aliases,region,org_level,priority,status\n"
        'csv_001,CSV组织,"[""别名1""]",示例市,市级,normal,active\n',
        encoding="utf-8",
    )

    import wechat_collector.io.import_orgs as import_module

    class _SessionFactory:
        def __init__(self, session):
            self._session = session

        def __call__(self):
            return self

        def __enter__(self):
            return self._session

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(import_module, "SessionLocal", _SessionFactory(db_session))

    count_first, skipped_first = import_orgs_from_csv(csv_path)
    count_second, skipped_second = import_orgs_from_csv(csv_path)

    assert count_first == 1
    assert skipped_first == 0
    assert count_second == 1
    assert skipped_second == 0
    assert len(org_service.list_organizations(db_session)) == 1
