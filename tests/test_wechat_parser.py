from pathlib import Path

from wechat_collector.parsers.wechat import (
    compute_content_hash,
    load_selector_config,
    normalize_wechat_url,
    parse_wechat_article_html,
)

SAMPLE_HTML_PATH = (
    Path(__file__).resolve().parents[1]
    / "samples"
    / "snapshots"
    / "wechat_article_sample.html"
)


def test_parse_wechat_article_sample() -> None:
    html = SAMPLE_HTML_PATH.read_text(encoding="utf-8")
    result = parse_wechat_article_html(
        html,
        url="https://mp.weixin.qq.com/s?__biz=abc123&mid=1&idx=1&sn=xyz&utm_source=noise",
        save_snapshot_on_error=False,
    )

    assert result.ok
    assert result.title == "关于2026年示例工作的通知"
    assert result.account_name == "示例市发展和改革委员会"
    assert result.cover_url == "https://example.com/cover.jpg"
    assert result.publish_time is not None
    assert "2026年示例工作" in (result.content_text or "")
    assert result.content_hash == compute_content_hash(result.content_text)
    assert result.canonical_url == "https://mp.weixin.qq.com/s?__biz=abc123&mid=1&idx=1"
    assert "<script>" not in (result.content_html or "")


def test_parse_wechat_fallback_selectors(tmp_path: Path) -> None:
    html = SAMPLE_HTML_PATH.read_text(encoding="utf-8")
    config = load_selector_config()
    config_without_og = {
        **config,
        "title": ["#activity-name"],
        "cover": [],
        "publish_time": ["#publish_time"],
    }

    result = parse_wechat_article_html(
        html,
        selector_config=config_without_og,
        save_snapshot_on_error=False,
        snapshot_dir=tmp_path,
    )

    assert result.title == "关于2026年示例工作的通知"
    assert result.publish_time is not None
    assert result.cover_url is None


def test_parse_failure_saves_snapshot(tmp_path: Path) -> None:
    result = parse_wechat_article_html(
        "<html><body><p>no article</p></body></html>",
        save_snapshot_on_error=True,
        snapshot_dir=tmp_path,
    )

    assert not result.ok
    assert "title_not_found" in result.errors
    assert "content_not_found" in result.errors
    assert list(tmp_path.glob("wechat_parse_fail_*.html"))


def test_parse_strips_wechat_hidden_content_styles() -> None:
    html = """
    <html><body>
      <h1 id="activity-name">测试标题</h1>
      <div id="js_name">测试公众号</div>
      <div id="js_content" style="visibility: hidden; opacity: 0;">
        <p>可见正文段落</p>
      </div>
    </body></html>
    """
    result = parse_wechat_article_html(html, save_snapshot_on_error=False)

    assert result.content_html is not None
    assert "visibility: hidden" not in result.content_html
    assert "opacity: 0" not in result.content_html
    assert "可见正文段落" in (result.content_text or "")


def test_normalize_wechat_url() -> None:
    assert (
        normalize_wechat_url("https://mp.weixin.qq.com/s?__biz=abc&sn=1&mid=1&idx=1&utm_source=x#comment")
        == "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1"
    )
