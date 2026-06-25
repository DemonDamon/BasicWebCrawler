# P8 调度 / 重试 / 风控

Plan-Id: 2026-06-25-wc-p8-scheduler
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P3, P4
阶段: 二 | 难度: ⭐⭐

## 目标
按优先级分级调度采集任务，失败指数退避，整体队列化降低风控风险（方案 §6）。

## 交付物
- `wechat_collector/scheduler/priority.py`：P0–P3 分级（方案 §6.1）：
  - P0 重点/监管/高频：高频发现+补采；P1 每日；P2 低频；P3 连续失败→人工队列。
- `wechat_collector/scheduler/retry.py`：指数退避（方案 §6.2）：
  - 第1次 10min、第2次 1h、第3次 6h、第4次 → manual。
- 任务取出策略接入 P3 `get_next_task`：按 priority 排序 + 退避到期过滤。
- 风控保护（方案 §6.3）：单 client 并发上限、单账号频率上限、已成功不重复采、全部队列化。
- 频率/并发参数走 config（可热调）。

## 验收
- [x] 失败任务按退避时间表重新可取；满 4 次进 manual。
- [x] 取任务遵守账号频率与并发上限（单测模拟）。

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p8-scheduler.plan.md`
