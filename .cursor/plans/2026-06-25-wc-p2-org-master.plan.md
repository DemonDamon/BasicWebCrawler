# P2 组织主数据 + 导入

Plan-Id: 2026-06-25-wc-p2-org-master
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P1
阶段: 一 | 难度: ⭐

## 目标
维护 3000+ 组织标准档案及其「组织 ↔ 公众号」映射，支撑发现召回与覆盖率统计。

## 交付物
- `wechat_collector/services/org_service.py`：组织 CRUD + 别名管理 + 公众号绑定。
- `wechat_collector/io/import_orgs.py`：从 CSV/Excel 批量导入组织（含 aliases JSON 列）。
- 一份示例模板 `samples/orgs_template.csv`（org_code, org_name, aliases, region, org_level, priority）。
- 单测覆盖：导入去重（org_code 幂等）、别名解析、一组织多公众号绑定。

## 设计要点（取方案 §4.1）
1. 一个组织对应多个公众号（organizations 1:N wechat_accounts）。
2. 公众号可改名/迁移 → wechat_accounts 保 alias_names + status + last_verified_at。
3. aliases 直接影响搜索召回，导入时做规范化（去空格/全半角）。
4. 提供「人工校准映射」接口（绑定/解绑 org-account）。

## 步骤
1. 写 org_service（基于 P1 ORM）。
2. 写导入脚本，支持幂等 upsert by org_code。
3. 单测 + 用示例 CSV 跑一遍导入。

## 验收
- [x] 导入示例 CSV → 组织入库，重复导入不产生重复行
- [x] 可为一个组织绑定多个公众号并查询
- [x] `pytest tests/test_org_service.py` 通过

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p2-org-master.plan.md`
