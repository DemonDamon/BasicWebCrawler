"""从 CSV 批量导入组织主数据（按 org_code 幂等 upsert）。"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from wechat_collector.db.base import SessionLocal
from wechat_collector.services import org_service


def import_orgs_from_csv(csv_path: Path) -> tuple[int, int]:
    created_or_updated = 0
    skipped = 0

    with SessionLocal() as db, csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"org_code", "org_name"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV must include columns: {sorted(required)}")

        for row in reader:
            org_code = (row.get("org_code") or "").strip()
            org_name = (row.get("org_name") or "").strip()
            if not org_code or not org_name:
                skipped += 1
                continue

            org_service.upsert_organization_by_code(
                db,
                org_code=org_code,
                org_name=org_name,
                aliases=row.get("aliases"),
                region=(row.get("region") or None),
                org_level=(row.get("org_level") or None),
                official_website=(row.get("official_website") or None),
                priority=(row.get("priority") or "normal"),
                status=(row.get("status") or "active"),
            )
            created_or_updated += 1

    return created_or_updated, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import organizations from CSV")
    parser.add_argument("csv_path", type=Path, help="Path to org CSV file")
    args = parser.parse_args(argv)

    if not args.csv_path.exists():
        print(f"File not found: {args.csv_path}", file=sys.stderr)
        return 1

    try:
        count, skipped = import_orgs_from_csv(args.csv_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Imported/updated: {count}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
