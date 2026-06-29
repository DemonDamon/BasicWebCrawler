"""为微信账号快速配置 RSSHub 路由。

用法示例（在项目根目录执行）：

    # 用 __biz 自动注册 freewechat 路由（推荐，biz 已知时无需手动填写）
    python -m wechat_collector.io.register_rsshub_routes --auto-freewechat

    # 为单个账号指定 wechat2rss 订阅 ID
    python -m wechat_collector.io.register_rsshub_routes \\
        --account-name "机器之心" \\
        --wechat2rss-id abc123def456

    # 查看所有账号的当前路由配置
    python -m wechat_collector.io.register_rsshub_routes --list
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from wechat_collector.db.base import SessionLocal
from wechat_collector.db.models import WechatAccount


def _find_account(db, name: str) -> WechatAccount | None:
    return db.scalar(
        select(WechatAccount).where(WechatAccount.account_name == name).limit(1)
    )


def cmd_list() -> int:
    with SessionLocal() as db:
        accounts = list(db.scalars(select(WechatAccount).order_by(WechatAccount.id)))

    col = max((len(a.account_name or "") for a in accounts), default=10) + 2
    print(f"{'账号名':<{col}}{'biz':<32}{'RSSHub 路由'}")
    print("-" * 80)
    for a in accounts:
        routes_str = ", ".join(
            f"{r.get('provider')}:{r.get('route', '')}"
            for r in (a.rsshub_routes or [])
        ) or "—"
        print(f"{(a.account_name or ''):<{col}}{(a.biz or '—'):<32}{routes_str}")
    return 0


def cmd_auto_freewechat(dry_run: bool = False) -> int:
    """
    对所有已有 biz 但尚未配置 freewechat 路由的账号，自动添加路由。
    freewechat 路由格式：/freewechat/profile/:biz
    """
    updated = 0
    skipped_no_biz = 0
    skipped_already = 0

    with SessionLocal() as db:
        accounts = list(db.scalars(select(WechatAccount).order_by(WechatAccount.id)))

        for account in accounts:
            if not account.biz:
                skipped_no_biz += 1
                continue

            routes: list[dict] = list(account.rsshub_routes or [])
            already_has = any(
                r.get("provider") == "freewechat" for r in routes
            )
            if already_has:
                skipped_already += 1
                continue

            new_route = {"provider": "freewechat", "route": f"/freewechat/profile/{account.biz}"}
            routes.append(new_route)

            if not dry_run:
                account.rsshub_routes = routes
            updated += 1
            print(f"{'[dry-run] ' if dry_run else ''}配置 {account.account_name}: {new_route['route']}")

        if not dry_run:
            db.commit()

    print(f"\n完成：新增 {updated} 个 | 跳过无biz {skipped_no_biz} 个 | 跳过已配置 {skipped_already} 个")
    if skipped_no_biz > 0:
        print(f"提示：{skipped_no_biz} 个账号还没有 biz，请先用插件采集各号的任意一篇文章。")
        print("      运行 python -m wechat_collector.io.show_biz_status 查看详情。")
    return 0


def cmd_set_wechat2rss(account_name: str, route_id: str) -> int:
    with SessionLocal() as db:
        account = _find_account(db, account_name)
        if not account:
            print(f"错误：找不到账号 '{account_name}'", file=sys.stderr)
            return 1

        routes: list[dict] = list(account.rsshub_routes or [])
        routes = [r for r in routes if r.get("provider") != "wechat2rss"]
        routes.append({"provider": "wechat2rss", "route": f"/wechat/wechat2rss/{route_id}"})
        account.rsshub_routes = routes
        db.commit()
        print(f"已为 {account_name} 配置 wechat2rss 路由: /wechat/wechat2rss/{route_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="为微信账号配置 RSSHub 路由")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="列出所有账号的 RSSHub 路由配置")

    p_auto = sub.add_parser("auto-freewechat", help="对已有 biz 的账号自动添加 freewechat 路由")
    p_auto.add_argument("--dry-run", action="store_true", help="只预览，不实际写入")

    p_w2r = sub.add_parser("set-wechat2rss", help="为账号设置 wechat2rss 订阅 ID")
    p_w2r.add_argument("--account-name", required=True, help="账号名")
    p_w2r.add_argument("--route-id", required=True, help="wechat2rss 订阅 ID")

    # 兼容旧式 flag 调用
    parser.add_argument("--list", action="store_true", help="列出所有路由（等价于 list 子命令）")
    parser.add_argument("--auto-freewechat", action="store_true", help="自动配置 freewechat（等价于 auto-freewechat）")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--account-name")
    parser.add_argument("--wechat2rss-id")

    args = parser.parse_args(argv)

    if args.cmd == "list" or getattr(args, "list", False):
        return cmd_list()
    if args.cmd == "auto-freewechat" or getattr(args, "auto_freewechat", False):
        return cmd_auto_freewechat(dry_run=getattr(args, "dry_run", False))
    if args.cmd == "set-wechat2rss":
        return cmd_set_wechat2rss(args.account_name, args.route_id)
    if getattr(args, "account_name", None) and getattr(args, "wechat2rss_id", None):
        return cmd_set_wechat2rss(args.account_name, args.wechat2rss_id)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
