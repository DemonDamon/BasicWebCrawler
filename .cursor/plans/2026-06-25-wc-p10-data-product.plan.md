# P10 数据产品化（摘要 / 检索 / 报表）

Plan-Id: 2026-06-25-wc-p10-data-product
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P4, P9
阶段: 三 | 难度: ⭐⭐⭐ | 长期迭代

## 目标
把采集到的文章转化为业务可用资产（方案 §9 阶段三）。

## 交付物（可分批）
- AI 摘要 / 关键词抽取 / 主题分类：复用现有 `mcp_server/llm_client.py` 调 LLM。
- 全文检索：先 PG 全文索引（tsvector）；可选向量化入库（复用现有知识库思路）。
- 订阅推送：按组织/关键词订阅，新文章触发通知。
- 覆盖率周报/月报：基于 P9 指标定时生成 Markdown 报表。
- 第三方数据源兜底接入（可选，商业源 provider 接口，复用 P7 provider 抽象）。
- MCP 工具暴露：把「按组织查文章/覆盖率/摘要」做成 FastMCP 工具，接入 Cursor/Claude。

## 验收
- 文章可生成摘要与关键词并入库。
- 可按组织+关键词全文检索。
- 自动产出一份覆盖率周报。

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p10-data-product.plan.md`
