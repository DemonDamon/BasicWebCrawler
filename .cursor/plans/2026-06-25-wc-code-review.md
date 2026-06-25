# wechat_collector P1–P9 代码审查报告

审查模型: claude-opus-4.6 (explore mode)
审查范围: wechat_collector/ 全部 50 个 .py、extension/ 4 个 .js + manifest、迁移 3 个、测试 10 个、alembic.ini、requirements-collector.txt
日期: 2026-06-25

---

## Critical（必须修复）

| # | 位置 | 问题 | 影响 |
|---|------|------|------|
| C1 | `extension/lib/` 未进版本库 (api.js, storage.js, parser.js) | **根因已查明**：文件在磁盘上确实存在并已实现，但被 `.gitignore` 的 `lib/`（Python 构建产物规则）误伤忽略。**已修复**：将规则改为 `/lib/` 仅限根目录，`extension/lib/` 现已可被 git 跟踪（待 commit）。原"插件完全不可用"判断成立但根因是 gitignore 作用域 bug，非未实现 |
| C2 | `article_service.py:60–77,98–101` | 去重命中（content_hash/canonical_url/url）时提前 return，不调用 `mark_success` | 带 candidate_id 的任务永久卡在 `processing`，队列阻塞 |
| C3 | `extension/background.js:127–131` | 成功入库后：`ingestArticle`（服务端已 mark success）+ 再次 `markTaskSuccess` | **机制已确认**（`lib/api.js:67` 透传 candidate_id → 服务端 `article_service:98-101` 已 mark success；客户端 `:130` 再 mark 撞 `success→success` 空转换抛错 → catch 里 `:136` 又 markTaskFailed 再次失败）。**一次成功采集会被报成错误**。仅影响 auto 路径（手动路径无 candidate_id）。未修，建议只在服务端 mark，移除客户端 markTaskSuccess |
| C4 | `discovery/providers/official_site.py:19–26` | `official_website` 来自 CSV/DB，服务端 `requests.get` 无 URL 校验 | SSRF：内网探测、云元数据访问 |
| C5 | `api/static/admin.html:63–71` | `innerHTML` 拼接 title/url/account_name 未转义 | Stored XSS：恶意标题可在管理员浏览器执行脚本 |

---

## High（高风险）

| # | 位置 | 问题 | 影响 |
|---|------|------|------|
| H1 | `config.py:14` | 默认 token = `"change-me-in-production"` | 未改 env 即等同无鉴权 |
| H2 | `api/deps.py:36` | Token 用 `!=` 比较，非 constant-time | 时序侧信道（理论风险） |
| H3 | `candidate_service.py:111–160` | `get_next_task` 用 `with_for_update()`；SQLite 锁语义弱，无 `SKIP LOCKED` | 多 worker 并发领取重复或阻塞 |
| H4 | `candidate_service.py` + `scheduler/limits.py` | `processing` 无超时回收；崩溃后 `account_recently_crawled` 永久挡住 | 账号级采集停摆 |
| H5 | `candidate_service.py:84–108` | enqueue 先查后插，无 `IntegrityError` 处理 | 并发入队同一 URL → 未捕获异常 → API 500 |
| H6 | `api/static/health.html:61–73` | `innerHTML` 渲染 account_name/org_name/alert.message | XSS（同 C5） |
| H7 | `article_service.py:79–101` | 文章 insert 与 candidate mark_success 两次 commit，非原子 | mark_success 失败时文章已入库、任务仍 processing |
| H8 | `extension/manifest.json:7–12` | `host_permissions`: `http://*/*`, `https://*/*` | Token 泄露面扩大 |
| H9 | `discovery/search_html.py` + discovery router | `POST /api/discovery/run` 触发对外 HTTP 无速率限制 | 可 DoS 自身或被封 IP |
| H10 | `db/base.py:10–16` | SQLite 未启用 `PRAGMA foreign_keys=ON` | 孤儿 org_id/account_id 可写入 |
| H11 | `api/routers/admin.py:37–44` | `/admin` 页面无鉴权 | 暴露 UI 结构（API 仍需 token） |

---

## Medium（需改进）

| # | 位置 | 问题 |
|---|------|------|
| M1 | `api/schemas.py` | URL 无格式校验；title/content_html 无长度上限 |
| M2 | `api/routers/candidates.py:53–72` | import 逐条 commit，无 FK 校验 org_id/account_id |
| M3 | `api/routers/admin.py:19–20` | limit/offset 无上下界（limit=999999999 拖垮 DB） |
| M4 | `api/routers/tasks.py:15` | priority 无枚举校验 |
| M5 | `monitoring/metrics.py:60–67` | `consecutive_failures` 实为全部 failed/manual/retrying 计数，指标误导 |
| M6 | `monitoring/metrics.py:108–125` | `average_collect_delay_hours` 全表扫描 Article |
| M7 | `monitoring/metrics.py:17–79` | `refresh_account_health` 每账号 6+ 次查询（3000 账号时 N+1） |
| M8 | `monitoring/alerts.py:28–97` | `GET /monitoring/alerts` 有写副作用（修改 health.status） |
| M9 | `monitoring/alerts.py:70` | `ilike("%parse%")` 在 SQLite 上行为/性能与 PG 不一致 |
| M10 | `db/models.py:80–113` | status/priority 无 DB CHECK 约束 |
| M11 | `db/models.py:97–98` | url unique + normalized_url unique 但 raw url 可能不一致 |
| M12 | `migrations/002:23–27` | `normalized_url` UNIQUE 但 nullable |
| M13 | `services/report_service.py:71–149` | `build_coverage_report` 10+ 次独立 COUNT |
| M14 | `services/org_service.py:141–145` | `list_organizations` 无分页 |
| M15 | `api/app.py` | 无 CORS、无 rate limit、无 request body 大小限制 |
| M16 | `api/routers/articles.py:10–42` | ingest 无 try/except；状态冲突未映射 HTTP 409 |
| M17 | `extension/background.js:174,216` | `busy` 存 chrome.storage.sync 非原子 |
| M18 | `extension/options.js:28` | Token 存 chrome.storage.sync（Google 账号同步扩散） |
| M19 | `tests/test_wechat_parser.py:3–8` | import compute_content_hash/normalize_wechat_url（可能未导出） |
| M20 | `tests/test_collector_models.py` | 未断言 discovery_source_stats 表 |

---

## Low（可后续优化）

| # | 位置 | 问题 |
|---|------|------|
| L1 | candidate_service.py:66–67 | `_utcnow()` 去 tz 用 naive datetime |
| L2 | scheduler/limits.py:28–37 | 限频只查 candidate.crawled_at 不查 Article |
| L3 | discovery/base.py:91–104 | `is_relevant_link` 短别名 ≥2 字符误匹配 |
| L4 | parsers/wechat.py:88–94 | 只剥 script/style/iframe，恶意 HTML 原样入库 |
| L5 | utils/url_normalize.py:33–35 | 非 wechat 域名也 normalize 返回 |
| L6 | io/import_orgs.py:39–40 | priority/status 无枚举校验 |
| L7 | alembic.ini:8 | 占位 sqlalchemy.url（runtime 被 env 覆盖） |
| L8 | requirements-collector.txt | 版本仅 `>=`，无上限/无 lock |
| L9 | requirements-collector.txt | 无 gunicorn/生产 ASGI 说明 |

---

## 测试覆盖缺口

| 场景 | 当前覆盖 |
|------|----------|
| 并发 `get_next_task`（两 session） | ❌ |
| `processing` 僵死与恢复 | ❌ |
| `ingest` duplicate + `candidate_id`（C2） | ❌ |
| `IntegrityError` on enqueue | ❌ |
| extension 与 API 集成（E2E） | ❌ |
| SSRF / URL 校验 | ❌ |
| admin 分页边界 | ❌ |
| PostgreSQL 集成 | ❌（仅内存 SQLite） |
| Alembic upgrade/downgrade 集成 | ❌ |
| `mark_failed` 从非 `processing` 状态 | ❌ |
| `article_service` 与 candidate_id 部分失败事务 | ❌ |

---

## 推荐修复优先级

1. **补全 `extension/lib/*`** + 修 C3（只在一处 mark success）
2. **修 C2**：去重返回时若 candidate_id 仍 processing → mark_success/ignored
3. **SSRF 防护**：official_website URL allowlist + 禁内网（C4）
4. **XSS 修复**：admin/health 页改用 textContent 或 DOMPurify（C5/H6）
5. **Token 安全**：强制生产 token + `secrets.compare_digest`（H1/H2）
6. **processing 超时回收** job（H4）
7. **enqueue 捕获 IntegrityError** 重试 merge（H5）
8. **生产 PostgreSQL** + 连接池 + SKIP LOCKED（H3）

---

## 总结

- **Critical 5 项**：其中 C1（extension/lib 缺失）和 C2/C3（状态机双重 mark/不 mark）是最影响功能的；C4/C5 是安全问题。
- **High 11 项**：主要集中在并发安全（H3/H4/H5）、鉴权（H1/H2）和 XSS（H6）。
- **当前测试 39 passed** 但覆盖面主要在单线程 happy path；并发、异常路径、集成测试基本空白。
- **架构层面**：SQLite 作为开发 DB 足够，但多 worker 生产必须切 PostgreSQL 并加 SKIP LOCKED。

---

*此文档供高阶模型复审使用，可按 severity 分批修复。*
