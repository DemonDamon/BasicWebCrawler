# 微信公众号定向采集子系统 — 使用手册

> 本文档面向**从零开始**的使用者，覆盖：环境初始化 → 导入公众号 → 启动服务 → 采集文章 → 查看结果。

---

## 目录

1. [系统架构一览](#1-系统架构一览)
2. [快速开始（5 分钟）](#2-快速开始5-分钟)
3. [环境配置](#3-环境配置)
4. [初始化数据库](#4-初始化数据库)
5. [导入公众号清单](#5-导入公众号清单)
6. [启动 API 服务](#6-启动-api-服务)
7. [Chrome 插件安装与配置](#7-chrome-插件安装与配置)
8. [采集文章](#8-采集文章)
   - [方式 A：手动单篇采集（M1）](#方式-a手动单篇采集m1)
   - [方式 B：插件自动队列采集（M2）](#方式-b插件自动队列采集m2)
   - [方式 C：命令行批量入队 + Worker 后台处理](#方式-c命令行批量入队--worker-后台处理)
9. [查看采集结果](#9-查看采集结果)
10. [Worker 常驻进程](#10-worker-常驻进程)
11. [常见问题](#11-常见问题)
12. [命令速查表](#12-命令速查表)

---

## 1. 系统架构一览

```
┌─────────────────────────────────────────────────────────────┐
│ Chrome 浏览器（登录微信网页版 / 公众号文章页）               │
│                                                             │
│  ┌──────────────────────────────────────┐                  │
│  │ extension/（Chrome MV3 插件）         │                  │
│  │  • M1 手动：采集当前打开的文章        │                  │
│  │  • M2 自动：轮询任务队列并自动打开   │                  │
│  └──────────────────┬───────────────────┘                  │
└─────────────────────┼───────────────────────────────────────┘
                      │ HTTP POST /api/articles
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ wechat_collector（FastAPI 服务，默认端口 8787）             │
│                                                             │
│  /api/articles    ← 接收插件推送的文章                      │
│  /api/crawl/      ← 插件自动模式轮询任务队列               │
│  /admin           ← 浏览器查看入库结果                      │
│  /docs            ← Swagger 在线接口文档                    │
│                                                             │
│  候选池（ArticleCandidate）── Worker 消费 ──→ 文章库        │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
              wechat_collector.db（SQLite）
              或远程 PostgreSQL（.env 配置）
```

**两种主要采集路径：**

| 路径 | 适用场景 | 需要微信登录 |
|------|----------|-------------|
| **浏览器插件**（M1/M2） | 日常采集、需要登录态的完整文章 | ✅ 需要 |
| **Worker + 命令行**（方式 C） | 批量入队公开可访问的链接 | ❌ 不需要（但受限） |

> 微信公众号文章的大部分链接在**未登录**时可以访问，Worker 路径主要用于处理这类公开链接。若遇到验证码或环境异常，需切换到插件路径。

---

## 2. 快速开始（5 分钟）

> ⚠️ **以下所有命令均在项目根目录下执行**（即 `BasicWebCrawler/` 目录，`wechat_collector/` 的上一级）：
> ```bash
> cd /path/to/BasicWebCrawler
> ```

```bash
# 1. 安装依赖
pip install -r requirements-collector.txt

# 2. 复制配置模板并编辑
cp .env.example .env
# 编辑 .env，把 COLLECTOR_API_TOKEN 改成自己生成的随机字符串（见第 3 节）

# 3. 初始化数据库（首次运行）
alembic upgrade head

# 4. 导入试点公众号
python -m wechat_collector.io.import_wechat_accounts samples/pilot_wechat_accounts.csv

# 5. 启动 API 服务（保持终端窗口开着）
uvicorn wechat_collector.api.app:app --reload --port 8787

# 6. 安装 Chrome 插件（见第 7 节），在浏览器里打开微信文章，点击「采集当前文章」
# 7. 访问 http://127.0.0.1:8787/admin 查看结果
```

---

## 3. 环境配置

> 📁 在项目根目录（`BasicWebCrawler/`）编辑 `.env` 文件：

```bash
# 数据库（默认用 SQLite，开发够用）
COLLECTOR_DB_URL=sqlite:///./wechat_collector.db

# 远程 PostgreSQL 示例（生产环境推荐）
# COLLECTOR_DB_URL=postgresql+psycopg2://user:password@localhost:5432/wechat_collector

# API 鉴权 Token，自己随机生成一个，插件和服务端保持一致
COLLECTOR_API_TOKEN=你的随机字符串

# ---- Worker 调度参数（可选，有默认值）----
# 两次抓取之间的随机等待范围（秒）
WORKER_MIN_DELAY_SECONDS=30
WORKER_MAX_DELAY_SECONDS=180
# 候选池为空时的轮询间隔（秒）
WORKER_IDLE_SLEEP_SECONDS=60
# HTTP 请求超时（秒）
WORKER_FETCH_TIMEOUT_SECONDS=20
```

**生成随机 Token：**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 4. 初始化数据库

> 📁 在项目根目录（`BasicWebCrawler/`）执行：

```bash
# 首次运行：执行所有迁移脚本，建表
alembic upgrade head

# 查看当前迁移版本
alembic current

# 重置数据库（会删除所有数据！）
rm wechat_collector.db && alembic upgrade head
```

---

## 5. 导入公众号清单

> 📁 在项目根目录（`BasicWebCrawler/`）执行。

### CSV 格式

```csv
org_code,org_name,account_name,aliases,priority
THU_AI,清华大学人工智能研究院,THU_AI_Lab,,high
MSRA,微软亚洲研究院,MSRAsia,,high
```

字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `org_code` | ✅ | 组织唯一标识，字母数字下划线 |
| `org_name` | ✅ | 组织全称 |
| `account_name` | ✅ | 微信公众号名称（如显示在文章头部的名字） |
| `aliases` | ❌ | 别名，多个用分号隔开 |
| `priority` | ❌ | `high` / `normal` / `low`，默认 `normal` |

### 导入命令

```bash
# 导入试点清单（49 个号）
python -m wechat_collector.io.import_wechat_accounts samples/pilot_wechat_accounts.csv

# 导入自定义清单
python -m wechat_collector.io.import_wechat_accounts 你的清单.csv

# 输出示例：
# Organizations upserted: 49, accounts created: 49, skipped: 0
```

> 重复执行是安全的，已存在的组织会 upsert（更新），不会重复创建。

---

## 6. 启动 API 服务

> 📁 在项目根目录（`BasicWebCrawler/`）执行，启动后**保持该终端窗口开着**。

```bash
# 开发模式（代码改动后自动重载）
uvicorn wechat_collector.api.app:app --reload --port 8787

# 生产模式（多 worker）
uvicorn wechat_collector.api.app:app --host 0.0.0.0 --port 8787 --workers 2
```

服务启动后可访问：

| 地址 | 说明 |
|------|------|
| `http://127.0.0.1:8787/healthz` | 健康检查 |
| `http://127.0.0.1:8787/admin` | 文章管理后台（输入 Token 后加载） |
| `http://127.0.0.1:8787/docs` | Swagger 接口文档 |
| `http://127.0.0.1:8787/redoc` | ReDoc 接口文档 |

> ⚠️ 访问 `/` 会返回 404，这是正常的，没有根路由。

---

## 7. Chrome 插件安装与配置

### 安装步骤

1. 打开 Chrome，地址栏输入 `chrome://extensions/`
2. 右上角开启「**开发者模式**」
3. 点击「**加载已解压的扩展程序**」
4. 选择本项目的 `extension/` 目录
5. 工具栏出现插件图标即安装成功

### 配置插件

1. 右键插件图标 →「**选项**」（或在扩展列表点击「详情」→「扩展程序选项」）
2. 填写：
   - **API Base URL**：`http://127.0.0.1:8787`（与服务启动的地址一致）
   - **API Token**：与 `.env` 中 `COLLECTOR_API_TOKEN` 完全一致
3. 点击保存

---

## 8. 采集文章

### 方式 A：手动单篇采集（M1）

**适合**：临时采集某一篇文章，或验证系统是否正常。

1. 在 Chrome 中打开任意微信文章（URL 格式：`https://mp.weixin.qq.com/s/...`）
2. 点击工具栏的插件图标
3. 点击「**采集当前文章**」
4. 等待弹窗显示「采集成功」
5. 到 `/admin` 查看入库结果

### 方式 B：插件自动队列采集（M2）

**适合**：批量处理已知 URL 列表，插件自动开标签页逐一采集。

**前提**：候选池中有 `pending` 任务（先用方式 C 或 API 入队）。

1. 先把 URL 批量入队（见方式 C）
2. 确保浏览器已登录微信网页版
3. 点击插件图标 →「**开始自动采集**」
4. 插件会自动：拉取任务 → 开标签页 → 解析 → 回报结果 → 关闭标签页 → 下一条
5. 想停止时点「**停止**」

### 方式 C：命令行批量入队 + Worker 后台处理

> 📁 以下命令均在项目根目录（`BasicWebCrawler/`）执行。

**适合**：有一批 URL 链接，无需打开浏览器，让 Worker 在后台自动处理。

**第一步：把 URL 入队**

```bash
# 将包含微信链接的文本文件入队
python -m wechat_collector.io.enqueue_wechat_urls urls.txt

# 绑定到指定组织（org_code 来自 CSV 导入时设置的值）
python -m wechat_collector.io.enqueue_wechat_urls urls.txt --org-code THU_AI

# 直接传入单条 URL（把 URL 写入临时文件）
echo "https://mp.weixin.qq.com/s/xxxxx" > /tmp/one.txt
python -m wechat_collector.io.enqueue_wechat_urls /tmp/one.txt
```

`urls.txt` 的内容格式没有要求，脚本会自动提取其中所有 `mp.weixin.qq.com/s/...` 链接：

```
今天看到一篇好文章：
https://mp.weixin.qq.com/s/abc123
另外还有：https://mp.weixin.qq.com/s/def456
```

**第二步：启动 Worker 处理**

```bash
# 启动常驻 Worker（默认随机间隔 30s~3min）
python -m wechat_collector.worker

# 调试模式（短间隔、详细日志）
python -m wechat_collector.worker --min-delay 5 --max-delay 15 --idle-sleep 10 --log-level DEBUG

# 按 Ctrl+C 优雅退出（会等当前任务完成再停止）
```

Worker 输出示例：
```
2026-06-26 10:38:50 [INFO] Worker 启动 | 抓取间隔 30–180s | 空队列轮询 60s
2026-06-26 10:39:23 [INFO] OK   [NEW] task=3 清华大学...深度学习研究进展  [总计 1 成功 / 0 失败]
2026-06-26 10:42:01 [INFO] OK   [DUP(url_exists)] task=4 ...              [总计 2 成功 / 0 失败]
2026-06-26 10:45:30 [INFO] 候选池为空（空转第 1 轮），60s 后再次轮询
```

---

## 9. 查看采集结果

### 方式一：Admin 后台

打开 `http://127.0.0.1:8787/admin`，输入 Token 后点「加载文章」。

### 方式二：API 接口

```bash
# 获取文章列表
curl -H "Authorization: Bearer 你的Token" \
     http://127.0.0.1:8787/api/articles

# 获取采集统计
curl -H "Authorization: Bearer 你的Token" \
     http://127.0.0.1:8787/api/coverage/summary
```

### 方式三：直接查数据库

```bash
# 查看文章总数
sqlite3 wechat_collector.db "SELECT COUNT(*) FROM articles;"

# 查看最新 10 篇
sqlite3 wechat_collector.db \
  "SELECT id, title, account_name, publish_time FROM articles ORDER BY id DESC LIMIT 10;"

# 查看候选池状态
sqlite3 wechat_collector.db \
  "SELECT status, COUNT(*) FROM article_candidates GROUP BY status;"
```

---

## 10. Worker 常驻进程

> 📁 在项目根目录（`BasicWebCrawler/`）执行。

Worker 是一个持续运行的后台进程，消费候选池（方式 C 入队的 URL），随机间隔抓取以避免被反爬识别。

### 启动参数

```bash
python -m wechat_collector.worker [选项]

选项：
  --min-delay  FLOAT   两次抓取间最短等待（秒，默认 30）
  --max-delay  FLOAT   两次抓取间最长等待（秒，默认 180）
  --idle-sleep FLOAT   队列为空时的轮询间隔（秒，默认 60）
  --timeout    INT     HTTP 请求超时（秒，默认 20）
  --log-level  LEVEL   日志级别：DEBUG/INFO/WARNING/ERROR（默认 INFO）
```

### 日志含义

| 日志 | 含义 |
|------|------|
| `[NEW] task=3 标题...` | 文章成功采集并**新增**入库 |
| `[DUP(url_exists)] task=4` | URL 已存在，跳过（正常） |
| `[DUP(content_hash)] task=5` | 内容相同的文章已存在，跳过（正常） |
| `FAIL task=6 err=wechat_verification_required` | 遇到验证码，候选标记为重试 |
| `FAIL task=7 err=parse_empty` | 页面解析不到内容（可能是非文章页） |
| `候选池为空（空转第 N 轮）` | 队列暂时没有任务，等待中 |

### 后台持续运行（nohup）

```bash
# 后台运行，日志写入文件
nohup python -m wechat_collector.worker > logs/worker.log 2>&1 &

# 查看 PID
echo $!

# 停止 Worker
kill <PID>
```

---

## 11. 常见问题

**Q：访问 `http://127.0.0.1:8787/` 返回 404？**  
A：正常，没有根路由。请访问 `/healthz`、`/admin` 或 `/docs`。

**Q：Worker 运行但候选池一直为空？**  
A：需要先通过插件手动采集，或用 `enqueue_wechat_urls` 脚本把微信文章 URL 写入候选池。

**Q：采集时遇到「环境异常」或「验证码」？**  
A：微信服务器检测到非浏览器请求。解决方法：
- 切换到**插件方式 A/B**（带真实浏览器 Cookie）
- 候选任务会自动进入重试队列，稍后 Worker 会再次尝试

**Q：Admin 后台填了 Token 但显示「加载失败」？**  
A：检查：① API 服务是否已启动；② Token 是否与 `.env` 里完全一致（无多余空格）。

**Q：`alembic upgrade head` 报错 `ModuleNotFoundError`？**  
A：确保在项目根目录执行，且已安装依赖：`pip install -r requirements-collector.txt`。

**Q：想重置所有数据重新开始？**  
```bash
rm wechat_collector.db
alembic upgrade head
python -m wechat_collector.io.import_wechat_accounts samples/pilot_wechat_accounts.csv
```

---

## 12. RSSHub 巡检配置（P10-B）

> 📁 在项目根目录（`BasicWebCrawler/`）执行。

自动巡检能定期发现各公众号的新文章，无需每次手动找链接。

### 前置：获取 `__biz`

每个公众号有一个唯一标识 `__biz`（藏在文章 URL 的参数里）。用插件采集每个号的任意一篇文章，`__biz` 就自动保存到数据库。查看进度：

```bash
python -m wechat_collector.io.show_biz_status
```

### 第一步：本地启动 RSSHub

```bash
# 方式 A：Docker（推荐）
docker run -d -p 1200:1200 --name rsshub diygod/rsshub

# 方式 B：npm（需要 Node.js >= 18）
npm install -g rsshub
rsshub start
```

验证：访问 `http://127.0.0.1:1200` 能看到 RSSHub 首页即成功。

### 第二步：配置 .env

```bash
RSSHUB_BASE_URL=http://127.0.0.1:1200
```

### 第三步：为账号配置 RSS 路由

**方式 A（推荐）：已有 biz 的账号一键批量配置 freewechat 路由**

```bash
# 预览（不实际写入）
python -m wechat_collector.io.register_rsshub_routes auto-freewechat --dry-run

# 正式执行
python -m wechat_collector.io.register_rsshub_routes auto-freewechat
```

**方式 B：为单个账号配置 wechat2rss 路由**（更稳定，需先在 [wechat2rss.xlab.app](https://wechat2rss.xlab.app) 获取订阅 ID）

```bash
python -m wechat_collector.io.register_rsshub_routes set-wechat2rss \
    --account-name "机器之心" \
    --route-id abc123def456

# 查看所有账号的路由配置
python -m wechat_collector.io.register_rsshub_routes list
```

**方式 C：通过 API 配置**（适合批量脚本调用）

```bash
curl -X PUT http://127.0.0.1:8787/api/accounts/1/rsshub_routes \
  -H "Authorization: Bearer 你的Token" \
  -H "Content-Type: application/json" \
  -d '{"routes": [{"provider": "freewechat", "route": "/freewechat/profile/MzA3..."}]}'
```

### 第四步：启动 RSS 巡检 Worker

```bash
# 默认每 30 分钟轮询一次
python -m wechat_collector.worker.rss_poller

# 自定义间隔（调试时可缩短）
python -m wechat_collector.worker.rss_poller --interval 300 --log-level DEBUG

# 后台持续运行
nohup python -m wechat_collector.worker.rss_poller > logs/rss_poller.log 2>&1 &
```

巡检日志示例：
```
2026-06-26 14:00:00 [INFO] RSS Poller 启动 | RSSHub=http://127.0.0.1:1200 | 巡检间隔 1800s
2026-06-26 14:00:00 [INFO] ── 第 1 轮巡检开始 ──
2026-06-26 14:00:15 [INFO] 第 1 轮完成 | 组织=12 新增=7 合并=23 跳过=2 错误=0
2026-06-26 14:00:15 [INFO] 等待 1800s 后开始下一轮…
```

### 完整流程图

```
插件采集文章 → biz 自动写入 DB
                ↓
register_rsshub_routes auto-freewechat
                ↓
rss_poller 每 30min 轮询各账号 RSS feed
                ↓ 发现新 URL → 入候选池
fetch_worker 自动处理 → 入库
                ↓
/admin 查看结果
```

---

## 12. 命令速查表

```bash
# ── 初始化 ──────────────────────────────────────
alembic upgrade head                        # 建表/迁移
python -m wechat_collector.io.import_wechat_accounts <csv>  # 导入公众号

# ── 启动服务 ─────────────────────────────────────
uvicorn wechat_collector.api.app:app --reload --port 8787   # 启动 API

# ── 入队 URL ─────────────────────────────────────
python -m wechat_collector.io.enqueue_wechat_urls <文件>    # 从文件提取并入队
python -m wechat_collector.io.enqueue_wechat_urls <文件> --org-code <代码>  # 绑定组织

# ── Worker 常驻 ───────────────────────────────────
python -m wechat_collector.worker                           # 默认参数启动
python -m wechat_collector.worker --min-delay 5 --max-delay 30 --log-level DEBUG  # 调试

# ── 一次性跑批 ────────────────────────────────────
python -m wechat_collector.io.run_fetch_candidates --limit 10  # 处理 10 条后退出

# ── 查看数据 ─────────────────────────────────────
sqlite3 wechat_collector.db "SELECT COUNT(*) FROM articles;"
sqlite3 wechat_collector.db "SELECT status, COUNT(*) FROM article_candidates GROUP BY status;"

# ── RSS 巡检 ──────────────────────────────────────
python -m wechat_collector.io.show_biz_status                      # 查看 biz 填充进度
python -m wechat_collector.io.register_rsshub_routes auto-freewechat  # 自动配置 freewechat 路由
python -m wechat_collector.io.register_rsshub_routes list          # 查看所有路由配置
python -m wechat_collector.worker.rss_poller                       # 启动 RSS 巡检（默认 30min 间隔）
python -m wechat_collector.worker.rss_poller --interval 300        # 调试模式（5min 间隔）

# ── 接口 ─────────────────────────────────────────
# http://127.0.0.1:8787/admin     文章后台
# http://127.0.0.1:8787/docs      Swagger 文档
# http://127.0.0.1:8787/healthz   健康检查
```
