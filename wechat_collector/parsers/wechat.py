"""微信公众号文章解析器（配置化选择器）。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from wechat_collector.utils.hashing import compute_content_hash
from wechat_collector.utils.url_normalize import normalize_wechat_url

_CONFIG_PATH = Path(__file__).resolve().parent / "wechat.json"
_SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "samples" / "snapshots"


@dataclass
class WechatParseResult:
    title: str | None = None
    account_name: str | None = None
    wechat_id: str | None = None
    biz: str | None = None
    url: str | None = None
    canonical_url: str | None = None
    publish_time: datetime | None = None
    cover_url: str | None = None
    summary: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    content_hash: str | None = None
    collected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.title and self.content_html and not self.errors)


def load_selector_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or _CONFIG_PATH
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data["wechat_article"]


def _select_meta(soup: BeautifulSoup, selector: str) -> str | None:
    if not selector.startswith("meta"):
        return None
    match = re.search(r"meta\[property=['\"]([^'\"]+)['\"]\]", selector)
    if not match:
        return None
    prop = match.group(1)
    tag = soup.find("meta", attrs={"property": prop})
    if tag and tag.get("content"):
        return str(tag["content"]).strip()
    return None


def _select_first(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        if selector.startswith("meta"):
            value = _select_meta(soup, selector)
            if value:
                return value
            continue
        node = soup.select_one(selector)
        if node:
            text = node.get_text(strip=True)
            if text:
                return text
    return None


def _select_content_node(soup: BeautifulSoup, selectors: list[str]) -> Tag | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return node
    return None


def _clean_content_node(node: Tag) -> Tag:
    clone = BeautifulSoup(str(node), "html.parser")
    root = clone.find(node.name) or clone
    for tag_name in ("script", "style", "iframe"):
        for unwanted in root.find_all(tag_name):
            unwanted.decompose()
    return root


def _parse_publish_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y年%m月%d日 %H:%M",
        "%Y年%m月%d日",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    iso = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso)
        return parsed.replace(tzinfo=None)
    except ValueError:
        return None


def _build_summary(content_text: str | None, limit: int = 200) -> str | None:
    if not content_text:
        return None
    compact = re.sub(r"\s+", " ", content_text.strip())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "…"


def save_parse_snapshot(html: str, reason: str, snapshot_dir: Path | None = None) -> Path:
    target_dir = snapshot_dir or _SNAPSHOT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_reason = re.sub(r"[^\w\-]+", "_", reason)[:40]
    path = target_dir / f"wechat_parse_fail_{timestamp}_{safe_reason}.html"
    path.write_text(html, encoding="utf-8")
    return path


def parse_wechat_article_html(
    html: str,
    *,
    url: str | None = None,
    selector_config: dict[str, Any] | None = None,
    save_snapshot_on_error: bool = True,
    snapshot_dir: Path | None = None,
) -> WechatParseResult:
    config = selector_config or load_selector_config()
    soup = BeautifulSoup(html, "html.parser")
    result = WechatParseResult(url=url, canonical_url=normalize_wechat_url(url))

    result.title = _select_first(soup, config.get("title", []))
    result.account_name = _select_first(soup, config.get("account_name", []))
    result.cover_url = _select_first(soup, config.get("cover", []))

    publish_raw = _select_first(soup, config.get("publish_time", []))
    result.publish_time = _parse_publish_time(publish_raw)

    content_node = _select_content_node(soup, config.get("content", []))
    if content_node is None:
        result.errors.append("content_not_found")
    else:
        cleaned = _clean_content_node(content_node)
        result.content_html = str(cleaned)
        result.content_text = cleaned.get_text("\n", strip=True)
        result.content_hash = compute_content_hash(result.content_text)
        result.summary = _build_summary(result.content_text)

    if not result.title:
        result.errors.append("title_not_found")

    if save_snapshot_on_error and result.errors:
        save_parse_snapshot(html, "_".join(result.errors), snapshot_dir=snapshot_dir)

    return result
