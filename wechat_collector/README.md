# 微信公众号定向采集子系统 — 使用手册

> 本文档面向**从零开始**的使用者，覆盖：环境初始化 → 导入公众号 → 启动服务 → 采集文章 → 查看结果。

---

## 目录

1. [系统架构一览](#1-系统架构一览)
2. [环境准备与快速上手（推荐）](#2-环境准备与快速上手推荐)
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
12. [Playwright 搜狗发现（推荐）](#12-playwright-搜狗发现推荐)
13. [命令速查表](#13-命令速查表)

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
│  /api/accounts/   ← 账号管理                                  │
│  /admin           ← 浏览器查看入库结果                      │
│  /docs            ← Swagger 在线接口文档                    │
│                                                             │
│  候选池（ArticleCandidate）                                 │
│    ↑ sogou_poller 发现新 URL 入队                          │
│    ↑ 插件/命令行手动入队                                    │
│    ↓ fetch_worker / 插件自动采集 消费 → 入库               │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
              wechat_collector.db（SQLite）
              或远程 PostgreSQL（.env 配置）
```

**三种主要采集路径：**


| 路径                              | 适用场景                | 需要微信登录     | 自动化程度               |
| ------------------------------- | ------------------- | ---------- | ------------------- |
| **浏览器插件**（M1/M2）                | 日常单篇/批量采集、完整文章      | ✅ 需要       | 半自动                 |
| **命令行 + Worker**（方式 C）          | 有已知 URL 批量处理        | ❌ 不需要（但受限） | 半自动                 |
| **Playwright 搜狗**（sogou_poller） | 真实浏览器从搜狗搜索发现 URL    | ❌ 不需要      | 全自动（推荐）             |


> 路径互补：搜狗发现负责找 URL，Worker / 插件负责打开并入库；需要登录态的内容仍靠插件。

### 推荐阅读顺序（小白向）

| 你的目标 | 从哪读起 |
|---------|---------|
| **第一次搭环境、跑通全自动采集** | 第 **2** 节（按步骤做）→ 第 **9** 节看结果 |
| 改 `.env`、Token、搜狗间隔 | 第 **3** 节 + `/admin/manage` 网页配置 |
| 只用 Chrome 插件手动采一篇 | 第 **7** 节 → 第 **8** 节方式 A |
| 搜狗发现排错、读懂日志 | 第 **12** 节 |
| 忘记命令 | 第 **13** 节速查表 |

---



## 2. 环境准备与快速上手（推荐）

> 📁 **以下所有命令均在项目根目录执行**（`BasicWebCrawler/`，不是 `wechat_collector/` 子目录）：
>
> ```bash
> cd /path/to/BasicWebCrawler
> ```

本节教你跑通**推荐路径**：**搜狗 Playwright 自动发现 URL → Worker 抓取入库 → Admin 阅读**。  
不需要 Docker，不需要 RSSHub；Chrome 插件可选（补采单篇时用）。

### 你需要准备什么

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS / Linux / Windows 均可 |
| Python | **3.10+**（建议 3.11 或 3.12；用 `python3 --version` 检查） |
| 磁盘 | Playwright Chromium 约 150MB；SQLite 数据库在项目根目录 |
| 网络 | 能访问搜狗微信搜索、`mp.weixin.qq.com` |
| 终端窗口 | 全自动模式需 **3 个终端** 同时开着（见下文） |

### 第一步：安装 Python 依赖

```bash
pip install -r requirements-collector.txt
```

若使用虚拟环境（推荐）：

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-collector.txt
```

### 第二步：安装 Playwright 浏览器（搜狗发现必做）

```bash
playwright install chromium
```

只需执行一次。未安装时运行 `sogou_poller` 会报错。

### 第三步：配置 `.env`

```bash
cp .env.example .env
```

编辑 `.env`，**至少**改这两项：

```bash
# 自己生成随机 Token（见下方命令），插件与 Admin 要用同一个
COLLECTOR_API_TOKEN=粘贴你的随机字符串

# 开启搜狗自动发现（默认示例里是注释掉的，必须打开）
SOGOU_PLAYWRIGHT_ENABLED=true
```

生成 Token：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

更多可调参数见 [第 3 节](#3-环境配置)，或在服务启动后打开 **`http://127.0.0.1:8787/admin/manage`** 图形化修改。

### 第四步：初始化数据库并导入公众号

```bash
alembic upgrade head
python -m wechat_collector.io.import_wechat_accounts samples/pilot_wechat_accounts.csv
```

成功时会看到类似 `Organizations upserted: 49, accounts created: ...`。

### 第五步：开三个终端，分别启动

| 终端 | 命令 | 作用 |
|------|------|------|
| **1 — API** | `uvicorn wechat_collector.api.app:app --reload --port 8787` | 提供 `/admin`、候选池、入库接口 |
| **2 — 发现** | `python -m wechat_collector.worker.sogou_poller` | 搜狗搜文章 → URL 写入候选池 |
| **3 — 抓取** | `python -m wechat_collector.worker` | 从候选池取 URL → 解析 → 入库 |

> 终端 2、3 的 `.env` 里需有 `SOGOU_PLAYWRIGHT_ENABLED=true`；终端 2 首次运行前建议先做下一步「养 cookie」。

**怎么算成功？**

```bash
# 候选池里有 pending（发现在工作）
sqlite3 wechat_collector.db "SELECT status, COUNT(*) FROM article_candidates GROUP BY status;"

# 文章数在增加（抓取在工作）
sqlite3 wechat_collector.db "SELECT COUNT(*) FROM articles;"
```

### 第六步：首次运行搜狗 — 养 cookie（重要）

搜狗可能弹验证码。**第一次**用有界面模式跑一轮：

```bash
SOGOU_HEADLESS=false python -m wechat_collector.worker.sogou_poller --once
```

在弹出的 Chromium 里完成验证码，等命令行显示本轮结束。之后 `.env` 保持 `SOGOU_HEADLESS=true`（或不设，默认 true），再常驻跑终端 2 即可。

### 第七步：在 Admin 查看文章

1. 浏览器打开 `http://127.0.0.1:8787/admin`
2. 粘贴与 `.env` 相同的 **API Token** → 点「加载文章」
3. 左侧选文章，右侧阅读正文

管理公众号清单、环境变量：`http://127.0.0.1:8787/admin/manage`

### 可选：不用搜狗，只用 Chrome 插件采单篇

适合临时补一篇、或验证系统是否正常：

1. 完成上面 **第一～四步** 和 **终端 1（API）**
2. 按 [第 7 节](#7-chrome-插件安装与配置) 安装 `extension/` 插件
3. 打开微信文章 → 插件点「采集当前文章」
4. 在 `/admin` 刷新查看

---



## 3. 环境配置

> 📁 在项目根目录（`BasicWebCrawler/`）编辑 `.env` 文件。  
> 也可启动 API 后访问 **`/admin/manage`** 在网页上修改（保存后需重启 Worker / sogou_poller 才生效）。

### 必填项

| 变量 | 说明 |
|------|------|
| `COLLECTOR_API_TOKEN` | 鉴权 Token；Admin、Chrome 插件、API 必须一致 |
| `SOGOU_PLAYWRIGHT_ENABLED` | 设为 `true` 才能跑搜狗发现（`sogou_poller`） |

### 常用可选项

```bash
# 数据库（默认 SQLite，文件在项目根目录）
COLLECTOR_DB_URL=sqlite:///./wechat_collector.db

# ---- Worker 抓取（终端 3）----
WORKER_MIN_DELAY_SECONDS=30
WORKER_MAX_DELAY_SECONDS=180
WORKER_IDLE_SLEEP_SECONDS=60
WORKER_FETCH_TIMEOUT_SECONDS=20
WORKER_MAX_ARTICLE_AGE_DAYS=14      # 丢弃过旧文章，0=不限制

# ---- 搜狗 Playwright 发现（终端 2）----
SOGOU_PLAYWRIGHT_ENABLED=true
SOGOU_POLL_INTERVAL_SECONDS=14400   # 每轮间隔，默认 4 小时；调试可改 600
SOGOU_HEADLESS=true                 # 首次养 cookie 时用 false
SOGOU_MAX_ARTICLE_AGE_DAYS=14
SOGOU_USER_DATA_DIR=.playwright/sogou
```

完整变量说明见项目根目录 **`.env.example`**。

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


| 字段             | 必填  | 说明                                    |
| -------------- | --- | ------------------------------------- |
| `org_code`     | ✅   | 组织唯一标识，字母数字下划线                        |
| `org_name`     | ✅   | 组织全称                                  |
| `account_name` | ✅   | 微信公众号名称（如显示在文章头部的名字）                  |
| `aliases`      | ❌   | 别名，多个用分号隔开                            |
| `priority`     | ❌   | `high` / `normal` / `low`，默认 `normal` |




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


| 地址                              | 说明                   |
| ------------------------------- | -------------------- |
| `http://127.0.0.1:8787/healthz` | 健康检查                 |
| `http://127.0.0.1:8787/admin`   | 文章阅读台（输入 Token 后加载） |
| `http://127.0.0.1:8787/admin/manage` | 公众号管理 + 环境配置 |
| `http://127.0.0.1:8787/docs`    | Swagger 接口文档         |
| `http://127.0.0.1:8787/redoc`   | ReDoc 接口文档           |


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

打开 `http://127.0.0.1:8787/admin`，输入 Token 后点「加载文章」。左侧列表点选文章，右侧可预览正文/HTML 图片、纯文本与元数据。

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



### 清空测试数据（开发用）

M1 的 `/admin` **只有列表、没有删除按钮**。本地调试想重来时，直接在项目根目录操作 SQLite（**不影响** `organizations` / `wechat_accounts` 等配置）：

```bash
# 只清空已入库文章（admin 列表会变空）
sqlite3 wechat_collector.db "DELETE FROM articles;"

# 可选：清空候选池，让同一 URL 可重新入队抓取
sqlite3 wechat_collector.db "DELETE FROM article_candidates;"
```

若只想丢弃旧候选、保留 org 配置，可将已成功项标为 `ignored` 而非整表删除：

```bash
sqlite3 wechat_collector.db \
  "UPDATE article_candidates SET status='ignored' WHERE status IN ('success','pending','retrying');"
```

---



## 10. Worker 常驻进程

> 📁 在项目根目录（`BasicWebCrawler/`）执行。  
> 在推荐流程里，这是 **终端 3**：消费 sogou_poller / 手动入队写入的 URL，抓取并入库。

Worker 是一个持续运行的后台进程，消费候选池中的 URL，随机间隔抓取以避免被反爬识别。

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


| 日志                                             | 含义                |
| ---------------------------------------------- | ----------------- |
| `[NEW] task=3 标题...`                           | 文章成功采集并**新增**入库   |
| `[DUP(url_exists)] task=4`                     | URL 已存在，跳过（正常）    |
| `[DUP(content_hash)] task=5`                   | 内容相同的文章已存在，跳过（正常） |
| `FAIL task=6 err=wechat_verification_required` | 遇到验证码，候选标记为重试     |
| `FAIL task=7 err=parse_empty`                  | 页面解析不到内容（可能是非文章页） |
| `候选池为空（空转第 N 轮）`                               | 队列暂时没有任务，等待中      |




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

**Q：访问** `http://127.0.0.1:8787/` **返回 404？**  
A：正常，没有根路由。请访问 `/healthz`、`/admin` 或 `/docs`。

**Q：Worker 运行但候选池一直为空？**  
A：Worker **只消费**候选池，不会自己找 URL。请先确认：

1. 终端 2 是否在跑 `python -m wechat_collector.worker.sogou_poller`
2. `.env` 里 `SOGOU_PLAYWRIGHT_ENABLED=true`
3. 是否已执行 `playwright install chromium` 并完成首次 headful 养 cookie
4. 或用 `enqueue_wechat_urls` / 插件手动入队 URL

**Q：采集时遇到「环境异常」或「验证码」？**  
A：微信服务器检测到非浏览器请求。解决方法：

- 切换到**插件方式 A/B**（带真实浏览器 Cookie）
- 候选任务会自动进入重试队列，稍后 Worker 会再次尝试

**Q：Admin 后台填了 Token 但显示「加载失败」？**  
A：检查：① API 服务是否已启动；② Token 是否与 `.env` 里完全一致（无多余空格）。

**Q：**`alembic upgrade head` **报错** `ModuleNotFoundError`**？**  
A：确保在项目根目录执行，且已安装依赖：`pip install -r requirements-collector.txt`。

**Q：想重置所有数据重新开始？**  

```bash
rm wechat_collector.db
alembic upgrade head
python -m wechat_collector.io.import_wechat_accounts samples/pilot_wechat_accounts.csv
```

---



## 12. Playwright 搜狗发现（推荐）

> 若已按 [第 2 节](#2-环境准备与快速上手推荐) 跑通，本节为**详细配置、日志解读与排错**。

当搜狗 HTTP 抓取被反爬拦截时，使用 **Playwright 真实浏览器**从搜狗微信搜索跟随跳转，解析真实的 `mp.weixin.qq.com/s/...` URL 并入候选池。

### 安装 Playwright

```bash
pip install -r requirements-collector.txt
playwright install chromium   # 首次需下载 Chromium（约 150MB）
```



### 配置（`.env`）

```bash
SOGOU_PLAYWRIGHT_ENABLED=true
SOGOU_POLL_INTERVAL_SECONDS=14400    # 默认 4 小时一轮
SOGOU_MAX_ARTICLES_PER_ACCOUNT=5    # 每账号每轮最多跟随 5 篇
SOGOU_USER_DATA_DIR=.playwright/sogou
SOGOU_HEADLESS=true                 # 首次养 cookie 时设为 false
# 只保留最近 N 天内的文章（SERP 与文章页双重过滤）
SOGOU_MAX_ARTICLE_AGE_DAYS=14
WORKER_MAX_ARTICLE_AGE_DAYS=14
# 已废弃：URL 带 tsn 会被搜狗重定向到首页，请保持 0 或不设置
SOGOU_TIME_RANGE_TSN=0
```



### 首次养 cookie（headful 手动过验证码）

搜狗可能弹出验证码。首次用有界面模式登录一次，cookie 会持久化到 `.playwright/sogou/`：

```bash
SOGOU_PLAYWRIGHT_ENABLED=true SOGOU_HEADLESS=false \
  python -m wechat_collector.worker.sogou_poller --once
```

在打开的 Chromium 里完成验证码后，等待一轮跑完即可。之后可改回 `SOGOU_HEADLESS=true` 常驻运行。

### 常驻运行

```bash
# 终端 1：API
uvicorn wechat_collector.api.app:app --host 0.0.0.0 --port 8787

# 终端 2：搜狗发现（每 4h 一轮，发现 URL 入候选池）
SOGOU_PLAYWRIGHT_ENABLED=true python -m wechat_collector.worker.sogou_poller

# 终端 3：候选池消费（fetch + parse + 入库）
python -m wechat_collector.worker

# 或：Chrome 插件开启「自动采集」，与 fetch_worker 二选一
```



### 发现策略

搜狗 **type=1「搜公众号」** 仅覆盖少量认证号，试点列表里绝大多数号会显示「暂无官方认证订阅号」，因此不可作为主路径。

当前实现为：

1. **多角度搜索**（默认 4 组）：`公众号名` → `名+2026年6月` → `名+2026` → `名+上月`（合并 SERP 后再过滤）
2. **type=2** + **sort=1**（按发布时间倒序）
3. 解析 SERP 中 `.all-time-y2` 发布者，**只保留目标号发的文章**
4. 用 `timeConvert('…')` 与文章页 `publish_time` 做 **新鲜度过滤**

> 为何不能只用公众号名？搜狗会把「X 加入 OMAHA 联盟」等**提及该号的旧文**排在前面，该号自己 6 月的新文反而要用「号+年月」或标题关键词才搜得到（你在搜狗手动搜标题就是这种情况）。



### 如何读懂日志

一轮搜索里若出现「跳过很多条」但 `发现=0`，**不一定是发错号**。典型情况：

| 日志含义 | 说明 |
|---------|------|
| `发布者不符` | 关键词搜到了别的公众号发的文章（正常，会被滤掉） |
| `过旧` | **已是目标号**，但发布时间早于 `SOGOU_MAX_ARTICLE_AGE_DAYS` |
| `目标号最近=YYYY-MM-DD（约 N 天前）` | 搜狗里该号最新一篇也超出窗口 → 需调大天数或用插件补采 |

例如 `OMAHA联盟` 在搜狗最新一篇约 2026-03-04，距今天超过 14 天，因此 `发现=0` 是预期行为。

**低频更新号**（月更、季更）建议把 `.env` 改为：

```bash
SOGOU_MAX_ARTICLE_AGE_DAYS=90
WORKER_MAX_ARTICLE_AGE_DAYS=90
```

**搜狗索引滞后**的号（如果 `目标号最近` 已是 2021 年）无法靠调天数解决，需用插件手动补采。

### 流程图

```
sogou_poller（Playwright 搜狗搜索 + 跳转解析）
        ↓ 真实 mp.weixin.qq.com URL → 候选池
fetch_worker / 插件自动采集
        ↓ 打开文章 → 解析 → 入库
/admin 查看结果
```



### 已知局限

- **不要**在搜狗 URL 上使用 `tsn=` 时间参数（会被重定向到首页，导致「发现=0」）；新鲜度靠 `SOGOU_MAX_ARTICLE_AGE_DAYS` 控制。
- 触发反爬时仅**跳过当前 org**，继续扫描后续公众号；该 org 已收集到的链接仍会入候选池。
- 搜狗收录有延迟，刚发布的文章可能暂时搜不到；InfoQ 等号需等收录或配合插件补采。
- 默认 **关闭**（`SOGOU_PLAYWRIGHT_ENABLED=false`），需显式开启。

---



## 13. 命令速查表

> 📁 所有命令均在项目根目录（`BasicWebCrawler/`）执行。

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
python -m wechat_collector.io.show_biz_status                      # 查看 biz 填充进度

# ── Playwright 搜狗发现 ───────────────────────────
SOGOU_PLAYWRIGHT_ENABLED=true python -m wechat_collector.worker.sogou_poller
SOGOU_HEADLESS=false SOGOU_PLAYWRIGHT_ENABLED=true python -m wechat_collector.worker.sogou_poller --once

# ── 接口 ─────────────────────────────────────────
# http://127.0.0.1:8787/admin     文章后台
# http://127.0.0.1:8787/docs      Swagger 文档
# http://127.0.0.1:8787/healthz   健康检查
```

