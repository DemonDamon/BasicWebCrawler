# P10-B：RSSHub 巡检发现层

Planned-with: claude-sonnet-4-5
日期：2026-06-26

---

## 背景与问题

现有发现层（搜狗/Bing/Baidu）对微信公众号**基本失效**（反爬）。  
用户有 49 个目标账号，需要每天自动发现新文章，不能全靠手动插件采集。

**解决方案**：通过本地 RSSHub 实例订阅第三方聚合平台（wechat2rss / freewechat），  
定期拉取 RSS feed → 提取新文章 URL → 入候选池 → Worker 自动处理。

**前置条件**：P10-A 已完成（账号有 `biz` 字段）

---

## 非目标

- 不自建微信爬虫（依赖第三方聚合平台的合规采集）
- 不实现 RSSHub 自身功能（作为黑盒调用）
- 不处理需要登录态的微信官方接口（留给插件 M2）

---

## 架构

```
巡检调度器（RSS Poller）
  ↓ 每 30min
RSSHub 本地实例（Docker）
  ├─ /wechat/wechat2rss/:id   ← 无反爬，需订阅 ID
  ├─ /freewechat/profile/:id  ← 需 __biz，有反爬但可限速
  └─ /wechat/mp/homepage/:biz ← 需 __biz + Cookie（可选）
  ↓ RSS XML
链接提取 → 去重 → 入候选池
  ↓
Worker（P9 已实现）→ fetch → parse → 入库
```

---

## 功能需求

### FR-1：`WechatAccount` 扩展 RSS 路由字段

在 `WechatAccount` 增加：
- `rsshub_routes: JSON | None` — 该账号可用的 RSSHub 路由列表，例如：
  ```json
  [
    {"provider": "wechat2rss", "route": "/wechat/wechat2rss/abc123"},
    {"provider": "freewechat",  "route": "/freewechat/profile/MzA3..."}
  ]
  ```

### FR-2：DB 迁移（004）

新增 `wechat_accounts.rsshub_routes` JSON 列。

### FR-3：RSSHub 发现提供者

新增 `wechat_collector/discovery/providers/rsshub.py`：

```python
class RSSHubDiscoveryProvider(DiscoveryProvider):
    name = "rsshub"
    
    def __init__(self, rsshub_base_url: str, ...): ...
    
    def discover(self, org: Organization, queries: list[str]) -> DiscoveryResult:
        # 遍历 org 的 wechat_accounts
        # 对每个有 rsshub_routes 的账号调用 RSSHub
        # 解析 RSS XML 提取文章链接
        ...
```

### FR-4：RSS 轮询调度器

新增 `wechat_collector/worker/rss_poller.py`：

- 独立于 fetch_worker，专门负责发现
- 每 N 分钟（默认 30min）轮询所有配置了 rsshub_routes 的账号
- 发现的新 URL 入候选池
- 支持 `python -m wechat_collector.worker.rss_poller`

### FR-5：账号 RSS 路由管理 API

```
POST /api/accounts/{id}/rsshub_routes   # 配置账号的 RSSHub 路由
GET  /api/accounts/{id}/rsshub_routes   # 查看当前路由配置
```

### FR-6：批量注册辅助脚本

`wechat_collector/io/register_rsshub_routes.py`：

- 从 `wechat2rss.xlab.app` 搜索账号（需人工辅助获取订阅 ID）
- 从 `freewechat.com` 检索 `__biz` → 自动构造 freewechat 路由
- 输出可直接导入的 CSV

---

## 验收标准

- [ ] AC-1：`python -m wechat_collector.worker.rss_poller` 启动后，对已配置路由的账号定期拉取并入队
- [ ] AC-2：候选池中出现来自 `rsshub` source 的新条目
- [ ] AC-3：重复 URL 不重复入队（利用现有 normalized_url 去重）
- [ ] AC-4：RSSHub 不可用时 Poller 打日志但不崩溃
- [ ] AC-5：Admin 页面或 API 可查看各账号的 RSS 发现命中率

---

## 实现计划

### Step 1：DB 迁移 004 — 加 `rsshub_routes` 列

```python
# migrations/versions/004_rsshub_routes.py
op.add_column("wechat_accounts", sa.Column("rsshub_routes", sa.JSON(), nullable=True))
```

### Step 2：`discovery/providers/rsshub.py`

- 依赖：`requests`（已有）、`xml.etree.ElementTree`（标准库）
- 解析 RSS 2.0 / Atom `<item>` → 提取 `<link>` 和 `<title>`
- 过滤非 `mp.weixin.qq.com` 链接
- 限速：每个路由请求后 sleep 随机 2~5s（防被 RSSHub 限速）

### Step 3：`worker/rss_poller.py`

- 复用 `fetch_worker.py` 的信号处理和 `_interruptible_sleep`
- 轮询周期：`RSS_POLL_INTERVAL_SECONDS`（默认 1800s = 30min）
- 每轮：查所有 `rsshub_routes IS NOT NULL` 的账号 → 逐一拉取 → 入候选池
- 打印统计：本轮发现 N 条，新增 M 条，已有 K 条

### Step 4：`config.py` 加 RSSHub 配置

```python
rsshub_base_url: str = "http://127.0.0.1:1200"
rss_poll_interval_seconds: int = 1800
rss_request_delay_min_seconds: float = 2.0
rss_request_delay_max_seconds: float = 5.0
```

### Step 5：`io/register_rsshub_routes.py`

帮助用户快速配置账号路由：
- 输入：账号名或 `__biz`
- 输出：自动构造 freewechat 路由（`/freewechat/profile/:biz`）
- wechat2rss 路由需要手动填入订阅 ID（脚本提供交互式引导）

### Step 6：RSSHub 部署文档

在 `wechat_collector/README.md` 新增「RSSHub 巡检配置」章节：

```bash
# 本地起 RSSHub（无需注册）
docker run -d -p 1200:1200 --name rsshub diygod/rsshub

# 设置 .env
RSSHUB_BASE_URL=http://127.0.0.1:1200

# 给账号配置路由
python -m wechat_collector.io.register_rsshub_routes --account-name "机器之心"

# 启动 RSS 巡检
python -m wechat_collector.worker.rss_poller
```

---

## 文件改动清单

| 文件 | 改动类型 |
|------|---------|
| `wechat_collector/db/models.py` | WechatAccount 加 rsshub_routes 字段 |
| `wechat_collector/migrations/versions/004_rsshub_routes.py` | 新增迁移 |
| `wechat_collector/discovery/providers/rsshub.py` | 新增 RSSHub provider |
| `wechat_collector/discovery/service.py` | 注册 rsshub provider |
| `wechat_collector/worker/rss_poller.py` | 新增 RSS 轮询 Worker |
| `wechat_collector/worker/__main__.py` | 保持不变（poller 独立入口） |
| `wechat_collector/config.py` | 新增 RSSHub 配置项 |
| `wechat_collector/api/routers/accounts.py` | 新增（rsshub routes CRUD） |
| `wechat_collector/api/app.py` | 注册新 router |
| `wechat_collector/io/register_rsshub_routes.py` | 新增批量注册脚本 |
| `wechat_collector/README.md` | 新增 RSSHub 配置章节 |
| `.env.example` | 新增 RSSHub 相关变量 |

---

## 风险

| 风险 | 概率 | 缓解 |
|------|------|------|
| wechat2rss 订阅 ID 需逐一手动获取 | 高 | 先走 freewechat 路线（用 `__biz` 自动构造） |
| freewechat 反爬触发 | 中 | 限速 2~5s，首次触发后回退到更长间隔 |
| RSSHub Docker 启动失败 | 低 | Poller 检测到不可达时记录警告但不崩溃 |
| RSS feed 内容滞后（非实时） | 中 | 预期接受，巡检是"批量发现"，实时靠插件 M1 |

---

## 依赖

- **前置**：P10-A 完成（账号有 `biz`）
- **外部**：Docker（运行 RSSHub）；可选 wechat2rss 订阅账号
- **新 Python 依赖**：无（`xml.etree.ElementTree` 标准库）
