"""常驻抓取 Worker：持续消费候选池，随机间隔防反爬，优雅退出。

启动方式：
    python -m wechat_collector.worker

参数说明（均可通过 .env 覆盖）：
    WORKER_MIN_DELAY_SECONDS  两次抓取之间最短等待（默认 30s）
    WORKER_MAX_DELAY_SECONDS  两次抓取之间最长等待（默认 180s）
    WORKER_IDLE_SLEEP_SECONDS 队列为空时的轮询间隔（默认 60s）
"""

from __future__ import annotations

import logging
import random
import signal
import sys
import time

import requests

from wechat_collector.config import get_settings
from wechat_collector.db.base import SessionLocal
from wechat_collector.discovery.search_html import DEFAULT_HEADERS
from wechat_collector.parsers.wechat import parse_wechat_article_html
from wechat_collector.services import candidate_service
from wechat_collector.services.article_service import (
    ArticleIngestInput,
    ClientContext,
    ingest_article,
)

logger = logging.getLogger("wechat_collector.worker")

FETCH_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://mp.weixin.qq.com/",
}

_SHUTDOWN = False  # SIGINT / SIGTERM 收到后置 True


def _install_signal_handlers() -> None:
    def _handler(signum: int, _frame: object) -> None:
        global _SHUTDOWN
        sig_name = signal.Signals(signum).name
        logger.info("收到信号 %s，完成当前任务后退出…", sig_name)
        _SHUTDOWN = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def _random_delay(min_s: float, max_s: float) -> float:
    """在 [min_s, max_s] 之间取随机浮点数，额外 ±5% 抖动防模式识别。"""
    base = random.uniform(min_s, max_s)
    jitter = base * random.uniform(-0.05, 0.05)
    return max(1.0, base + jitter)


def _fetch_one(timeout: int) -> tuple[bool, str]:
    """
    从候选池取一条任务并完整处理。
    返回 (success, description)。
    """
    with SessionLocal() as db:
        task = candidate_service.get_next_task(db)
        if task is None:
            return False, "queue_empty"

        url = task.url
        task_id = task.id
        try:
            resp = requests.get(url, headers=FETCH_HEADERS, timeout=timeout)
            resp.raise_for_status()
            html = resp.text

            if "环境异常" in html or "验证码" in html:
                raise ValueError("wechat_verification_required")

            parsed = parse_wechat_article_html(html, url=url)
            if not parsed.content_text and not parsed.title:
                raise ValueError("parse_empty")

            result = ingest_article(
                db,
                ArticleIngestInput(
                    title=parsed.title or task.title or "未命名",
                    account_name=parsed.account_name,
                    url=url,
                    canonical_url=parsed.canonical_url,
                    publish_time=parsed.publish_time,
                    cover_url=parsed.cover_url,
                    summary=parsed.summary,
                    content_html=parsed.content_html,
                    content_text=parsed.content_text,
                    content_hash=parsed.content_hash,
                    org_id=task.org_id,
                    account_id=task.account_id,
                    candidate_id=task.id,
                    source="fetch_worker",
                ),
                ClientContext(client_id="fetch_worker"),
            )

            tag = "NEW" if result.created else f"DUP({result.duplicate_reason})"
            desc = f"[{tag}] task={task_id} {parsed.title or url[:60]}"
            return True, desc

        except Exception as exc:  # noqa: BLE001
            candidate_service.mark_failed(db, task_id, fail_reason=str(exc)[:200])
            return False, f"task={task_id} err={exc}"


def run_worker(
    *,
    min_delay: float | None = None,
    max_delay: float | None = None,
    idle_sleep: float | None = None,
    fetch_timeout: int | None = None,
) -> None:
    """Worker 主循环，持续运行直到收到停止信号。"""
    cfg = get_settings()
    min_delay = min_delay if min_delay is not None else cfg.worker_min_delay_seconds
    max_delay = max_delay if max_delay is not None else cfg.worker_max_delay_seconds
    idle_sleep = idle_sleep if idle_sleep is not None else cfg.worker_idle_sleep_seconds
    fetch_timeout = fetch_timeout if fetch_timeout is not None else cfg.worker_fetch_timeout_seconds

    _install_signal_handlers()

    stats = {"total": 0, "success": 0, "failed": 0, "idle_rounds": 0}
    logger.info(
        "Worker 启动 | 抓取间隔 %.0f–%.0fs | 空队列轮询 %.0fs",
        min_delay, max_delay, idle_sleep,
    )

    while not _SHUTDOWN:
        ok, desc = _fetch_one(fetch_timeout)

        if desc == "queue_empty":
            stats["idle_rounds"] += 1
            if stats["idle_rounds"] % 5 == 1:
                logger.info(
                    "候选池为空（空转第 %d 轮），%.0fs 后再次轮询",
                    stats["idle_rounds"], idle_sleep,
                )
            _interruptible_sleep(idle_sleep)
            continue

        # 有任务
        stats["idle_rounds"] = 0
        stats["total"] += 1
        if ok:
            stats["success"] += 1
            logger.info("OK   %s  [总计 %d 成功 / %d 失败]", desc, stats["success"], stats["failed"])
        else:
            stats["failed"] += 1
            logger.warning("FAIL %s  [总计 %d 成功 / %d 失败]", desc, stats["success"], stats["failed"])

        delay = _random_delay(min_delay, max_delay)
        logger.debug("等待 %.1fs 后继续…", delay)
        _interruptible_sleep(delay)

    logger.info(
        "Worker 已停止 | 共处理 %d 条（成功 %d / 失败 %d）",
        stats["total"], stats["success"], stats["failed"],
    )


def _interruptible_sleep(seconds: float) -> None:
    """可被信号中断的 sleep，每 1s 检查一次 _SHUTDOWN 标志。"""
    deadline = time.monotonic() + seconds
    while not _SHUTDOWN and time.monotonic() < deadline:
        time.sleep(min(1.0, deadline - time.monotonic()))


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="微信文章常驻抓取 Worker")
    parser.add_argument("--min-delay", type=float, help="最短等待秒数（默认来自配置）")
    parser.add_argument("--max-delay", type=float, help="最长等待秒数（默认来自配置）")
    parser.add_argument("--idle-sleep", type=float, help="空队列轮询间隔秒数")
    parser.add_argument("--timeout", type=int, help="HTTP 请求超时秒数")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    run_worker(
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        idle_sleep=args.idle_sleep,
        fetch_timeout=args.timeout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
