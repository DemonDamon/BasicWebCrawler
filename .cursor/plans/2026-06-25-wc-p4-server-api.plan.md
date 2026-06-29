# P4 服务端 API + 鉴权

Plan-Id: 2026-06-25-wc-p4-server-api
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P2, P3
阶段: 一 | 难度: ⭐⭐

## 目标
提供插件与发现层对接的 FastAPI 服务：入库、任务分发、状态回报、健康/覆盖率查询、人工导入。

## 接口（方案 §4.5）
| 接口 | 方法 | 用途 |
|---|---|---|
| /api/articles | POST | 接收采集正文（入 articles，content_hash 去重） |
| /api/candidates | POST | 接收新发现链接（入候选池，URL 去重） |
| /api/candidates/import | POST | 人工批量导入链接（兜底） |
| /api/crawl/tasks/next | GET | 取下一个 pending 任务 |
| /api/crawl/tasks/{id}/success | POST | 标记成功 |
| /api/crawl/tasks/{id}/failed | POST | 标记失败（记 fail_reason/retry） |
| /api/accounts/health | GET | 公众号健康状态 |
| /api/coverage/report | GET | 覆盖率报表 |
| /admin/articles | GET | 简单后台列表（M1 验收用） |

## 鉴权（方案 §4.5）
- Header `X-API-Token` 校验（来自 config，不写死）。
- 记录操作者/插件版本/client_id（请求头透传，写入审计字段）。
- Token 仅放行采集相关接口。

## 交付物
- `wechat_collector/api/app.py` + routers（articles/candidates/tasks/health/coverage/admin）。
- pydantic schema 校验请求体（对齐方案 §4.4 采集字段）。
- 最简后台页（Jinja2 或返回 JSON + 一个静态 HTML 列表）。
- 接口集成测试（FastAPI TestClient）。

## 验收
- [x] 启动 `uvicorn wechat_collector.api.app:app` 全接口可调
- [x] 无 Token / 错 Token → 401
- [x] POST 重复文章不重复入库
- [x] `pytest tests/test_api.py` 通过

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p4-server-api.plan.md`
