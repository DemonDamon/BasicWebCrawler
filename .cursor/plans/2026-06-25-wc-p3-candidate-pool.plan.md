# P3 候选池 + 状态机 + 去重

Plan-Id: 2026-06-25-wc-p3-candidate-pool
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P1, P2
阶段: 一 | 难度: ⭐⭐

## 目标
对所有来源发现的文章链接做统一去重、排队、状态管理，作为采集队列的事实来源。

## 交付物
- `wechat_collector/services/candidate_service.py`：入池/取下一个任务/标记状态/重试入队。
- `wechat_collector/utils/url_normalize.py`：微信 URL 标准化（保留 `/s/` 关键参数，去 chksm/scene/sn 等噪声参数）。
- `wechat_collector/utils/hashing.py`：content_hash（正文规范化后 sha256）。
- 单测：URL 标准化等价类、去重命中、状态机非法跃迁拦截。

## 状态机（方案 §4.3）
`pending → processing → success | failed`；`failed → retrying → processing`；`→ manual`；`→ ignored`。
用 `never` 风格穷尽校验非法转移（参考 typescript-exhaustive-switch 思路，Python 用显式映射表 + 抛错）。

## 去重规则（方案 §4.3）
1. normalized_url unique 入池去重。
2. 多来源命中同一 URL → 合并 source 列表（articles/candidates 记 source 多值）。
3. 正文 content_hash 二次去重（入 articles 时）。

## 验收
- [x] 同一文章不同 query 参数 → 归一为一条候选
- [x] `get_next_task(priority)` 按优先级返回 pending 并置 processing
- [x] 状态机非法跃迁抛错
- [x] `pytest tests/test_candidate_service.py tests/test_url_normalize.py` 通过

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p3-candidate-pool.plan.md`
