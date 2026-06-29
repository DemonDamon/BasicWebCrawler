"""组织优先级分级（方案 §6.1）。"""

from __future__ import annotations

from wechat_collector.db.models import Organization

PRIORITY_TIERS = {
    "high": "P0",
    "normal": "P1",
    "low": "P2",
}


def org_priority_tier(org: Organization | None) -> str:
    if org is None:
        return "P2"
    return PRIORITY_TIERS.get(org.priority or "normal", "P1")


def is_p0_org(org: Organization | None) -> bool:
    return org_priority_tier(org) == "P0"
