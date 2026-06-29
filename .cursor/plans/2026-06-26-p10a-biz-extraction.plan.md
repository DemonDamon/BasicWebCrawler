# P10-A：`__biz` 自动提取与账号匹配

Planned-with: claude-sonnet-4-5
日期：2026-06-26

---

## 背景与问题

`WechatAccount` 表已有 `biz` 字段（P1 建表时预留），但当前始终为 NULL。  
`__biz` 是微信公众号的**唯一标识符**，是 RSSHub 巡检（P10-B）的前提条件。  
获取路径：每篇文章 URL 或页面 meta 中均携带 `__biz` 参数。

**目标**：让系统在日常采集过程中自动积累 `__biz`，无需人工填写。

---

## 非目标

- 不从搜索引擎反查 `__biz`（反爬风险高）
- 不强制要求所有账号都有 `__biz`（无文章的账号暂时跳过）
- 不修改数据库 Schema（字段已存在）

---

## 功能需求

### FR-1：文章入库时自动提取 `__biz`

- 从文章 URL（`?__biz=` 或 `/s?__biz=`）提取 `__biz`
- 若能匹配到对应 `WechatAccount`（按 `account_name`）且其 `biz` 为 NULL，则写入

### FR-2：扩展采集时提取并上报 `__biz`

- `parser.js` 从页面 `<meta property="og:url">` 或 URL 参数提取 `__biz`
- `background.js` 在 ingestPayload 里附加 `biz` 字段上报
- 服务端 `ArticleIngestBody` 增加 `biz` 字段，`article_service` 写入关联账号

### FR-3：`biz` 批量补齐辅助脚本

- `wechat_collector/io/show_biz_status.py`：打印各账号的 `biz` 填充情况
- 方便用户判断哪些账号还需手动补充

---

## 验收标准

- [ ] AC-1：采集一篇文章后，对应 `WechatAccount.biz` 自动填充
- [ ] AC-2：已有 `biz` 的账号不会被覆盖
- [ ] AC-3：`python -m wechat_collector.io.show_biz_status` 输出各账号状态
- [ ] AC-4：无 `__biz` 的文章 URL 不报错，静默跳过
- [ ] AC-5：现有测试（39 条）不回归

---

## 实现计划

### Step 1：`utils/url_normalize.py` 加 `extract_biz()` 工具函数

```python
def extract_biz(url: str) -> str | None:
    """从微信文章 URL 中提取 __biz 参数。"""
```

### Step 2：`services/article_service.py` 入库时自动回填 `biz`

在 `ingest_article()` 里：
1. 调用 `extract_biz(url)`
2. 若有结果 → 查找匹配的 `WechatAccount`（按 `account_id` 或 `account_name`）
3. 若账号 `biz` 为 NULL → `UPDATE wechat_accounts SET biz=? WHERE id=?`

### Step 3：`api/schemas.py` 的 `ArticleIngestBody` 加 `biz` 字段

```python
biz: str | None = None  # 从扩展上报的 __biz
```

### Step 4：`extension/lib/parser.js` 提取 `__biz`

```javascript
// 从 og:url meta 或当前 URL 参数提取
biz: extractBiz(url),
```

### Step 5：`extension/background.js` 上报 `biz`

```javascript
const ingestPayload = {
  ...article,
  biz: article.biz || null,
};
```

### Step 6：`wechat_collector/io/show_biz_status.py`

```
账号名                  biz                       状态
机器之心                MzA3MDM3NjE5NQ==          ✅ 已采集
清华大学人工智能研究院  NULL                       ⏳ 待采集
...
统计：已填 12 / 49 个
```

---

## 文件改动清单

| 文件 | 改动类型 |
|------|---------|
| `wechat_collector/utils/url_normalize.py` | 新增 `extract_biz()` |
| `wechat_collector/services/article_service.py` | ingest 时自动回填 biz |
| `wechat_collector/api/schemas.py` | ArticleIngestBody 加 biz 字段 |
| `extension/lib/parser.js` | 提取 `__biz` |
| `extension/background.js` | 上报 `biz` |
| `wechat_collector/io/show_biz_status.py` | 新增（查看状态脚本） |

---

## 风险

- 部分文章 URL 格式为 `/s/shortcode`，不含 `__biz`，需从页面 meta 提取（parser.js 已能访问页面 DOM）
- 账号名匹配：若同一账号有多个名称变体，可能匹配到错误账号 → 优先按 `account_id` 匹配，`account_name` 作为 fallback

---

## 依赖

- 无新依赖
- 前置：无（独立可实施）
