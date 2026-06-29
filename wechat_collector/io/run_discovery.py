"""多源发现 CLI。"""

from __future__ import annotations

import argparse
import sys

from wechat_collector.db.base import SessionLocal
from wechat_collector.discovery.service import discover_for_active_organizations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run multi-source discovery for organizations")
    parser.add_argument("--limit", type=int, default=20, help="Max organizations to scan")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        summaries = discover_for_active_organizations(db, limit=args.limit)

    total_created = sum(item.created for item in summaries)
    total_merged = sum(item.merged for item in summaries)
    print(f"Organizations scanned: {len(summaries)}")
    print(f"Candidates created: {total_created}, merged: {total_merged}")
    for item in summaries:
        if item.created or item.merged or item.errors:
            print(
                f"- {item.org_name}: created={item.created}, merged={item.merged}, "
                f"sources={item.by_source}, disabled={item.disabled_sources}, errors={item.errors}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
