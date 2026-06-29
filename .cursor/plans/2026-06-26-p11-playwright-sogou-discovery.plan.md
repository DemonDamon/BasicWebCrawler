# P11：Playwright 搜狗发现层

Planned-with: claude-opus-4.8

## 背景与问题

当前采集系统的「处理层」（插件 / fetch_worker）已稳定可用，但**发现层全部碰壁**：

| 已尝试方案 | 失败原因 |
|-----------|---------|
| RSSHub `/freewechat` | freewechat.com 对爬虫返回 403 |
| freewechat.com 批量入队 | 内容是审查存档，全是 2025 年旧文章 |
| 搜狗 HTTP 抓取（`search_html`）| 非浏览器 UA → 搜狗反爬拦截 |
| 插件 executeScript 提取搜狗链接 | 链接是 `weixin.sogou.com/link?url=混淆码`，无法解码 |
| `mp.weixin.qq.com/mp/profile_ext` | 需微信客户端打开 |

WorkBuddy 提出用 **真实浏览器（Playwright）** 绕过搜狗反爬：真实 Chromium 自动执行 JS、跟随 302 跳转，能把搜狗跳转链接解析成真实的 `mp.weixin.qq.com/s/...`。这正是发现层缺口的解法。

## 对 Sonnet 初版方案的 6 项优化

1. **同步 Playwright（`playwright.sync_api`），不用 async**
   - 项目全部是同步代码（SQLAlchemy sync、`DiscoveryProvider.discover()` 同步）。
   - async 会强制把 DB 调用包进事件循环，徒增复杂度和 bug 面。

2. **实现为 `DiscoveryProvider` 子类，复用现有框架**
   - 新 `SogouPlaywrightDiscoveryProvider(DiscoveryProvider)`，返回 `DiscoveryResult`。
   - 直接套用现有 `candidate_service.enqueue_candidate`、`is_relevant_link`、`_record_source_run`，**零数据库结构改动**。
   - 新 worker `sogou_poller.py` 镜像 `rss_poller.py` 的结构（信号处理 / 可中断 sleep / 轮次日志）。

3. **持久化浏览器上下文（`launch_persistent_context` + `user_data_dir`）—— 可靠性核心**
   - 搜狗会在出验证码后要求 cookie/SNUID。持久化 profile 后：首次 headful 手动过一次验证码 → 之后 headless 复用 session 长期有效。
   - Sonnet 初版每次全新 context，会频繁触发验证码。

4. **单浏览器实例跨账号复用**
   - 一轮巡检只启动一个 browser，串行处理多个账号，结束统一关闭。
   - Sonnet 初版按账号开关浏览器，慢且易被识别。

5. **验证码检测 + 优雅降级**
   - 检测到反爬页（`antispider` / 验证码关键词）时：记录告警、停止本轮、不再硬刷，避免封 IP。
   - 默认 env flag 关闭（`SOGOU_PLAYWRIGHT_ENABLED=false`），显式开启才跑。

6. **保守限速 + 诚实记录局限**
   - 每账号每轮最多跟随 N=5 篇跳转，文章间随机延迟 1.5–3s，账号间 3–6s。
   - 轮询间隔默认 4h（远长于 RSS 的 30min）。
   - **已知局限**：搜狗文章搜索（type=2）按相关性而非时间排序，可能混入旧文；靠 `is_relevant_link` + 候选池去重兜底，必要时人工补直链。

## 需求（FR）与验收标准（AC）

- **FR-1**：新增同步 Playwright provider，输入账号名 → 输出真实 `mp.weixin.qq.com/s/...` URL 列表。
  - **AC-1**：对「机器之心」运行，返回 ≥1 条可访问的真实微信文章 URL。
- **FR-2**：新增 `sogou_poller` worker，遍历 49 个试点账号，发现 URL 入候选池。
  - **AC-2**：跑一轮后 `article_candidates` 新增 pending 候选，且全部属于试点账号（`is_relevant_link` 过滤通过）。
- **FR-3**：与现有 `fetch_worker` / 插件自动采集协同，候选被正常消化入库。
  - **AC-3**：`sogou_poller` + `fetch_worker` 同时跑，文章表新增记录，来源标记为 `sogou_playwright`。
- **FR-4**：验证码 / 反爬时优雅降级，不崩溃、不硬刷。
  - **AC-4**：人为触发反爬页时，worker 记录告警并跳过本轮，进程存活。
- **FR-5**：默认关闭，env flag 显式开启。
  - **AC-5**：未设 `SOGOU_PLAYWRIGHT_ENABLED=true` 时，poller 启动即提示「未启用」并退出。

## 实施步骤

### 步骤 1：依赖与配置
- `requirements.txt` 增加 `playwright`（注明需 `playwright install chromium`，~150MB）。
- `config.py` 新增：
  - `sogou_playwright_enabled: bool = False`
  - `sogou_poll_interval_seconds: int = 14400`（4h）
  - `sogou_max_articles_per_account: int = 5`
  - `sogou_user_data_dir: str = ".playwright/sogou"`
  - `sogou_headless: bool = True`
- `.env.example` 同步新增上述项 + 说明首次需 headful 过验证码。

### 步骤 2：Provider 实现
`wechat_collector/discovery/providers/sogou_playwright.py`
- `class SogouPlaywrightDiscoveryProvider(DiscoveryProvider)`，`name = "sogou_playwright"`。
- `__init__` 接收一个已打开的 Playwright `page`（由 poller 注入，实现浏览器复用）。
- `discover(org, queries)`：
  1. 对 org 的账号名调 `org_service.get_search_names`。
  2. `page.goto("https://weixin.sogou.com/weixin?type=2&query={name}")`。
  3. 检测反爬页 → 返回 `DiscoveryResult(error="antispider")`。
  4. `page.eval_on_selector_all(".news-list h3 a", "els => els.map(e=>e.href)")` 取跳转链接。
  5. 对前 N 条：`page.goto(link)` 跟随跳转 → 读 `page.url`，命中 `mp.weixin.qq.com/s` 则收集 → `page.go_back()` + 随机延迟。
  6. 用 `extract_wechat_links` / `normalize_wechat_url` 归一去重，组装 `CandidateLink(source="sogou_playwright")`。

### 步骤 3：Worker 实现
`wechat_collector/worker/sogou_poller.py`（镜像 `rss_poller.py`）
- env flag 未开 → 打印提示并 `return`（AC-5）。
- `launch_persistent_context(user_data_dir, headless=cfg.sogou_headless)` 启动单实例。
- 遍历活跃试点 org（复用 `joinedload(Organization.wechat_accounts)`）。
- 每 org 调 provider.discover → `is_relevant_link` 过滤 → `enqueue_candidate(source="sogou_playwright")`。
- `result.error == "antispider"` → 告警 + `break` 本轮（AC-4）。
- `_record_source_run(db, "sogou_playwright", accepted)`。
- 信号处理 / `_interruptible_sleep` / 轮次统计日志，全部复用 rss_poller 模式。
- `__main__` 入口：`python -m wechat_collector.worker.sogou_poller`，支持 `--interval` `--log-level` `--once`。

### 步骤 4：文档
- `wechat_collector/README.md` 新增「Playwright 搜狗发现」章节：
  - 安装：`pip install playwright && playwright install chromium`
  - 首次：`SOGOU_HEADLESS=false python -m wechat_collector.worker.sogou_poller --once` 手动过验证码养 cookie。
  - 常驻：`SOGOU_PLAYWRIGHT_ENABLED=true python -m wechat_collector.worker.sogou_poller`
  - 三终端协同图：sogou_poller（发现）+ fetch_worker（处理）+ uvicorn（API）。

### 步骤 5：验证
- 单测 provider 解析逻辑（mock page，验证 URL 提取/归一/去重）。
- 手动 `--once` 跑「机器之心」验证 AC-1/AC-2。
- 与 fetch_worker 联跑验证 AC-3。
- 断网 / 改 selector 模拟反爬验证 AC-4。

## 风险与应对

| 风险 | 应对 |
|------|------|
| 搜狗验证码 | 持久化 profile + 首次 headful 手动过；检测到即降级 |
| headless 被识别 | `--no-sandbox`、随机 UA、可切 headful |
| 搜索结果含旧文 | `is_relevant_link` + 候选池去重；人工补直链兜底 |
| Chromium 体积/CI | env flag 默认关闭，CI 不装 Playwright |
| 账号搜不到 | 跳过记录，保留插件手动采集路径 |

## 不做（Out of Scope）
- 不抓 `mp/profile_ext` 历史页（需微信客户端）。
- 不替换插件自动采集，二者互补：Playwright 管发现，插件/fetch_worker 管处理。
- 不引入分布式 / 代理池（试点 49 号规模无需）。

## 追溯
- 上游缺口记录见 P10-B（RSSHub 失败）。
- Plan-Id 锚点：`2026-06-26-p11-playwright-sogou-discovery`
