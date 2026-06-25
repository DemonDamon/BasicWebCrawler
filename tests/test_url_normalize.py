import pytest

from wechat_collector.utils.url_normalize import is_same_wechat_article, normalize_wechat_url


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (
            "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=111&chksm=xxx",
            "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=222&scene=1",
            True,
        ),
        (
            "http://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1#comment",
            "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1",
            True,
        ),
        (
            "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1",
            "https://mp.weixin.qq.com/s?__biz=abc&mid=2&idx=1",
            False,
        ),
    ],
)
def test_normalize_wechat_url_equivalence(left: str, right: str, expected: bool) -> None:
    assert is_same_wechat_article(left, right) is expected
    if expected:
        assert normalize_wechat_url(left) == normalize_wechat_url(right)


def test_normalize_wechat_url_strips_tracking_params() -> None:
    normalized = normalize_wechat_url(
        "https://mp.weixin.qq.com/s?__biz=abc123&mid=1&idx=1&sn=xyz&utm_source=noise&chksm=abc"
    )
    assert normalized == "https://mp.weixin.qq.com/s?__biz=abc123&mid=1&idx=1"
    assert "sn=" not in normalized
    assert "utm_source" not in normalized
