# P9 覆盖率与健康度监控

Plan-Id: 2026-06-25-wc-p9-monitoring
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P6, P7, P8
阶段: 二 | 难度: ⭐⭐

## 目标
全量无法保证时让缺口「可见、可追踪、可补救」（方案 §4.7）。

## 指标（方案 §4.7）
- 账号覆盖率（已确认公众号/组织数）
- 链接发现量（每日）
- 正文采集成功率（success/候选总数）
- 失败重试成功率
- 疑似漏采账号数
- 人工补采任务数
- 平均采集延迟（发布→入库）

## 交付物
- `wechat_collector/monitoring/metrics.py`：定时计算指标写入 `account_health` + 汇总表。
- 异常规则引擎（方案 §4.7）：
  - 高频账号 3 天无更新 → 复查队列
  - 连续失败超阈值 → 降频+报警
  - 大量解析失败 → 提示修复解析器
  - 搜索源连续为空 → 切源信号（给 P7）
  - 关键词命中不同公众号名 → 改名人工确认
- `/api/coverage/report` + `/api/accounts/health` 返回真实指标（升级 P4 占位实现）。
- 后台健康度页面（列表 + 预警标记）。

## 验收
- [x] 后台可看覆盖率/成功率/疑似漏采账号。
- [x] 构造连续失败/长期无更新数据 → 触发对应预警。

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p9-monitoring.plan.md`
