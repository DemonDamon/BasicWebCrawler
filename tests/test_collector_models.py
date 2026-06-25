"""Verify wechat_collector database models and migrations."""

from wechat_collector.db import models
from wechat_collector.db.base import Base


def test_models_importable() -> None:
    assert models.Organization.__tablename__ == "organizations"
    assert models.WechatAccount.__tablename__ == "wechat_accounts"
    assert models.ArticleCandidate.__tablename__ == "article_candidates"
    assert models.Article.__tablename__ == "articles"
    assert models.AccountHealth.__tablename__ == "account_health"


def test_all_tables_registered() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "organizations",
        "wechat_accounts",
        "article_candidates",
        "articles",
        "account_health",
    }
    assert expected.issubset(table_names)
