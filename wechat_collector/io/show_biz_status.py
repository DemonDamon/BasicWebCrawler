"""查看各微信账号的 __biz 填充状态。

用法（在项目根目录执行）：
    python -m wechat_collector.io.show_biz_status
"""

from __future__ import annotations

from sqlalchemy import select

from wechat_collector.db.base import SessionLocal
from wechat_collector.db.models import WechatAccount


def main() -> int:
    with SessionLocal() as db:
        accounts = list(
            db.scalars(select(WechatAccount).order_by(WechatAccount.id))
        )

    if not accounts:
        print("数据库中暂无公众号记录，请先运行 import_wechat_accounts。")
        return 0

    total = len(accounts)
    filled = [a for a in accounts if a.biz]
    empty = [a for a in accounts if not a.biz]

    col_name = max(len(a.account_name or "") for a in accounts) + 2
    col_biz = 30

    header = f"{'账号名':<{col_name}}{'__biz':<{col_biz}}状态"
    print(header)
    print("-" * len(header))

    for a in accounts:
        biz_str = a.biz or "—"
        status = "✅ 已填充" if a.biz else "⏳ 待采集"
        print(f"{(a.account_name or ''):<{col_name}}{biz_str:<{col_biz}}{status}")

    print()
    print(f"统计：已填充 {len(filled)} / {total} 个账号")

    if empty:
        print(f"\n尚未填充的账号（{len(empty)} 个），请用插件采集这些账号的任意一篇文章：")
        for a in empty[:10]:
            print(f"  - {a.account_name}")
        if len(empty) > 10:
            print(f"  ... 还有 {len(empty) - 10} 个")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
