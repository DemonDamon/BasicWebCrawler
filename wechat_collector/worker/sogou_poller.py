"""Playwright 搜狗发现 Worker：用真实浏览器从搜狗搜索发现微信文章 URL 并入候选池。

与 fetch_worker / 插件自动采集的分工：
  sogou_poller  → 负责「发现」：搜狗搜索 + 跳转解析 → 写入候选池
  fetch_worker / 插件 → 负责「处理」：打开文章页 → 解析 → 入库

启动方式（在项目根目录执行）：
    SOGOU_PLAYWRIGHT_ENABLED=true python -m wechat_collector.worker.sogou_poller

首次养 cookie（headful 手动过验证码）：
    SOGOU_PLAYWRIGHT_ENABLED=true SOGOU_HEADLESS=false \\
        python -m wechat_collector.worker.sogou_poller --once

参数：
    --interval   两次全量巡检之间的间隔秒数（默认 14400s = 4h）
    --once       只跑一轮后退出
    --log-level  日志级别（默认 INFO）
"""

from __future__ import annotations

import logging
import random
import signal
import sys
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from wechat_collector.config import get_settings
from wechat_collector.db.base import SessionLocal
from wechat_collector.db.models import Organization
from wechat_collector.discovery.base import is_relevant_link
from wechat_collector.discovery.providers.sogou_playwright import (
    DEFAULT_USER_AGENT,
    SogouPlaywrightDiscoveryProvider,
)
from wechat_collector.discovery.service import _record_source_run
from wechat_collector.services import candidate_service

logger = logging.getLogger("wechat_collector.sogou_poller")

_SHUTDOWN = False


def _install_signal_handlers() -> None:
    def _handler(signum: int, _frame: object) -> None:
        global _SHUTDOWN
        logger.info("收到信号 %s，完成当前轮次后退出…", signal.Signals(signum).name)
        _SHUTDOWN = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def _interruptible_sleep(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while not _SHUTDOWN and time.monotonic() < deadline:
        time.sleep(min(1.0, deadline - time.monotonic()))


def _sleep_between_accounts() -> None:
    cfg = get_settings()
    delay = random.uniform(
        cfg.sogou_account_delay_min_seconds,
        cfg.sogou_account_delay_max_seconds,
    )
    _interruptible_sleep(delay)


def _get_active_organizations(db) -> list[Organization]:
    orgs = db.scalars(
        select(Organization)
        .options(joinedload(Organization.wechat_accounts))
        .where(Organization.status == "active")
        .order_by(Organization.id)
    ).unique().all()
    return [org for org in orgs if org.wechat_accounts]


def run_poll_round(provider: SogouPlaywrightDiscoveryProvider) -> dict[str, int]:
    """执行一轮全量搜狗发现，返回统计。"""
    stats = {"orgs": 0, "created": 0, "merged": 0, "skipped": 0, "errors": 0}

    with SessionLocal() as db:
        orgs = _get_active_organizations(db)
        if not orgs:
            return stats

        stats["orgs"] = len(orgs)

        for org in orgs:
            if _SHUTDOWN:
                break

            result = provider.discover(org, [])

            if result.error == "antispider":
                stats["errors"] += 1
                logger.warning(
                    "检测到搜狗反爬/验证码，停止本轮 | org=%s",
                    org.org_name,
                )
                _record_source_run(db, "sogou_playwright", 0, "antispider")
                break

            if result.error:
                stats["errors"] += 1
                logger.warning("org=%s sogou 发现错误: %s", org.org_name, result.error)

            accepted = 0
            merged = 0
            skipped = 0
            for link in result.links:
                if not is_relevant_link(link, org):
                    skipped += 1
                    stats["skipped"] += 1
                    continue
                try:
                    account_id = org.wechat_accounts[0].id if org.wechat_accounts else None
                    _, created = candidate_service.enqueue_candidate(
                        db,
                        url=link.url,
                        org_id=org.id,
                        account_id=account_id,
                        title=link.title,
                        source=link.source,
                    )
                except ValueError:
                    skipped += 1
                    stats["skipped"] += 1
                    continue
                if created:
                    stats["created"] += 1
                    accepted += 1
                else:
                    stats["merged"] += 1
                    merged += 1

            if result.links or result.error:
                _record_source_run(db, "sogou_playwright", accepted, result.error)

            logger.info(
                "org=%s 发现=%d 新增=%d 合并=%d 跳过=%d",
                org.org_name,
                len(result.links),
                accepted,
                merged,
                skipped,
            )

            _sleep_between_accounts()

    return stats


def run_poller(*, interval: int | None = None, once: bool = False) -> None:
    cfg = get_settings()

    if not cfg.sogou_playwright_enabled:
        logger.info(
            "Playwright 搜狗发现未启用。请在 .env 中设置 SOGOU_PLAYWRIGHT_ENABLED=true"
        )
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        logger.error(
            "未安装 playwright。请执行: pip install playwright && playwright install chromium"
        )
        raise SystemExit(1) from exc

    poll_interval = interval if interval is not None else cfg.sogou_poll_interval_seconds
    user_data_dir = Path(cfg.sogou_user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    _install_signal_handlers()

    logger.info(
        "Sogou Poller 启动 | headless=%s | profile=%s | 巡检间隔 %ds",
        cfg.sogou_headless,
        user_data_dir,
        poll_interval,
    )

    round_count = 0

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=cfg.sogou_headless,
            user_agent=DEFAULT_USER_AGENT,
            locale="zh-CN",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            while not _SHUTDOWN:
                round_count += 1
                logger.info("── 第 %d 轮搜狗发现开始 ──", round_count)

                provider = SogouPlaywrightDiscoveryProvider(page)
                stats = run_poll_round(provider)

                if stats["orgs"] == 0:
                    logger.info("暂无活跃试点组织，跳过本轮")
                else:
                    logger.info(
                        "第 %d 轮完成 | 组织=%d 新增=%d 合并=%d 跳过=%d 错误=%d",
                        round_count,
                        stats["orgs"],
                        stats["created"],
                        stats["merged"],
                        stats["skipped"],
                        stats["errors"],
                    )

                if once:
                    break

                logger.info("等待 %ds 后开始下一轮…", poll_interval)
                _interruptible_sleep(poll_interval)
        finally:
            context.close()

    logger.info("Sogou Poller 已停止，共完成 %d 轮巡检", round_count)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="微信公众号 Playwright 搜狗发现 Worker")
    parser.add_argument("--interval", type=int, help="巡检间隔秒数（默认来自配置）")
    parser.add_argument("--once", action="store_true", help="只跑一轮后退出")
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

    run_poller(interval=args.interval, once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
