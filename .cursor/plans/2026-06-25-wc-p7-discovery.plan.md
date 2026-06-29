# P7 多源发现

Plan-Id: 2026-06-25-wc-p7-discovery
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P3, P4
阶段: 二 | 难度: ⭐⭐⭐（中高，反爬+噪声）

## 目标
尽量发现目标组织相关的微信文章链接，只产出候选链接，不保证正文采集成功（方案 §4.2）。

## 发现源（可插拔 provider 接口）
- `wechat_collector/discovery/base.py`：`DiscoveryProvider.discover(org) -> List[CandidateLink]`。
- providers：
  - `bing.py` / `baidu.py`：`site:mp.weixin.qq.com/s "组织名/别名" 关键词`（方案 §4.2 搜索策略）。
  - `sogou_wechat.py`：搜狗微信（标注稳定性一般）。
  - `official_site.py`：组织官网链接发现（从 P2 official_website）。
  - `manual.py`：人工导入（走 P4 `/api/candidates/import`）。
- 结果统一写入候选池（P3），来源标 source，含 discovered_at/status=pending。

## 设计要点
1. 多源融合，绝不依赖单一入口（方案 §7.4）。
2. 别名扩展查询：用 P2 的 aliases 生成多条 query 提升召回。
3. 噪声过滤：只保留 `mp.weixin.qq.com/s` 链接；标题相关性粗筛。
4. 反爬：发现层降频 + 失败标记 + 切源（方案 §4.7 搜索源无结果→切源）。

## 验收
- [x] 给定若干组织，能从至少 2 个源产出候选链接并入候选池去重。
- [x] 单源连续为空触发告警/切源信号（交给 P9）。

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p7-discovery.plan.md`
