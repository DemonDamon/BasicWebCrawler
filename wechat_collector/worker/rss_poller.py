"""RSS 巡检 Worker：定期拉取各账号 RSSHub feed，发现新文章 URL 入候选池。

与 fetch_worker.py 的分工：
  rss_poller  → 负责"发现"：从 RSS 获取新文章 URL，写入候选池
  fetch_worker → 负责"处理"：从候选池取 URL，fetch + parse + 入库

启动方式（在项目根目录执行）：
    python -m wechat_collector.worker.rss_poller

参数：
    --interval   两次全量巡检之间的间隔秒数（默认 1800s = 30min）
    --log-level  日志级别（默认 INFO）
"""

from __future__ import annotations

import logging
import signal
import sys
import time

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from wechat_collector.config import get_settings
from wechat_collector.db.base import SessionLocal
from wechat_collector.db.models import Organization, WechatAccount
from wechat_collector.discovery.providers.rsshub import RSSHubDiscoveryProvider
from wechat_collector.discovery.service import _record_source_run
from wechat_collector.discovery.base import is_relevant_link
from wechat_collector.services import candidate_service

logger = logging.getLogger("wechat_collector.rss_poller")

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


def _get_orgs_with_rsshub_routes(db) -> list[Organization]:
    """查询所有拥有配置了 rsshub_routes 账号的活跃组织。"""
    account_ids_subq = (
        select(WechatAccount.org_id)
        .where(
            WechatAccount.rsshub_routes.is_not(None),
            WechatAccount.org_id.is_not(None),
        )
        .distinct()
        .scalar_subquery()
    )
    orgs = db.scalars(
        select(Organization)
        .options(joinedload(Organization.wechat_accounts))
        .where(
            Organization.status == "active",
            Organization.id.in_(account_ids_subq),
        )
        .order_by(Organization.id)
    ).unique().all()
    return list(orgs)


def run_poll_round(provider: RSSHubDiscoveryProvider) -> dict[str, int]:
    """执行一轮全量巡检，返回统计 {created, merged, skipped, orgs}。"""
    stats = {"orgs": 0, "created": 0, "merged": 0, "skipped": 0, "errors": 0}

    with SessionLocal() as db:
        orgs = _get_orgs_with_rsshub_routes(db)
        if not orgs:
            return stats

        stats["orgs"] = len(orgs)

        for org in orgs:
            result = provider.discover(org, [])

            if result.error:
                stats["errors"] += 1
                logger.warning("org=%s rsshub 发现错误: %s", org.org_name, result.error)
                _record_source_run(db, "rsshub", 0, result.error)
                break  # RSSHub 不可达时跳出整轮

            accepted = 0
            for link in result.links:
                if not is_relevant_link(link, org):
                    stats["skipped"] += 1
                    continue
                try:
                    _, created = candidate_service.enqueue_candidate(
                        db,
                        url=link.url,
                        org_id=org.id,
                        title=link.title,
                        source=link.source,
                    )
                except ValueError:
                    stats["skipped"] += 1
                    continue
                if created:
                    stats["created"] += 1
                    accepted += 1
                else:
                    stats["merged"] += 1

            if result.links:
                _record_source_run(db, "rsshub", accepted)

    return stats


def run_poller(*, interval: int | None = None) -> None:
    cfg = get_settings()
    poll_interval = interval if interval is not None else cfg.rss_poll_interval_seconds

    _install_signal_handlers()
    provider = RSSHubDiscoveryProvider()

    logger.info(
        "RSS Poller 启动 | RSSHub=%s | 巡检间隔 %ds",
        cfg.rsshub_base_url, poll_interval,
    )

    round_count = 0
    while not _SHUTDOWN:
        round_count += 1
        logger.info("── 第 %d 轮巡检开始 ──", round_count)

        stats = run_poll_round(provider)

        if stats["orgs"] == 0:
            logger.info("暂无配置 RSSHub 路由的账号，跳过本轮")
        else:
            logger.info(
                "第 %d 轮完成 | 组织=%d 新增=%d 合并=%d 跳过=%d 错误=%d",
                round_count,
                stats["orgs"], stats["created"], stats["merged"],
                stats["skipped"], stats["errors"],
            )

        logger.info("等待 %ds 后开始下一轮…", poll_interval)
        _interruptible_sleep(poll_interval)

    logger.info("RSS Poller 已停止，共完成 %d 轮巡检", round_count)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="微信公众号 RSS 巡检 Worker")
    parser.add_argument("--interval", type=int, help="巡检间隔秒数（默认来自配置）")
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

    run_poller(interval=args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
