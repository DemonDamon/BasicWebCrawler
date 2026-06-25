"""微信文章 URL 标准化（用于候选池去重）。"""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# 文章身份参数；sn/chksm/scene 等分享追踪参数不参与去重
KEEP_QUERY_PARAMS = frozenset({"__biz", "mid", "idx"})
STRIP_QUERY_PARAMS = frozenset(
    {
        "sn",
        "chksm",
        "scene",
        "key",
        "ascene",
        "devicetype",
        "version",
        "lang",
        "pass_ticket",
        "exportkey",
    }
)


def normalize_wechat_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.strip()}")

    if "mp.weixin.qq.com" not in parsed.netloc:
        normalized = parsed._replace(fragment="", scheme="https")
        return urlunparse(normalized)

    query = parse_qs(parsed.query, keep_blank_values=False)
    filtered: dict[str, str] = {}
    for key, values in query.items():
        if key in STRIP_QUERY_PARAMS:
            continue
        if key in KEEP_QUERY_PARAMS and values:
            filtered[key] = values[0]
        elif key.startswith("utm_"):
            continue

    normalized = parsed._replace(
        fragment="",
        query=urlencode(filtered),
        scheme="https",
        netloc="mp.weixin.qq.com",
    )
    return urlunparse(normalized)


def is_same_wechat_article(url_a: str | None, url_b: str | None) -> bool:
    left = normalize_wechat_url(url_a)
    right = normalize_wechat_url(url_b)
    return bool(left and right and left == right)
