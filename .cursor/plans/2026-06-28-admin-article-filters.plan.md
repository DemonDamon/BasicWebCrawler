# Admin 阅读台：公众号 + 时间筛选

Planned-with: composer-2.5-fast

## 背景

当前 `/admin` 阅读台只有左侧列表内的**关键词搜索**（标题 / 公众号名），且为纯前端过滤。用户希望在顶栏「采集阅读台」与下方列表/正文区之间增加**独立筛选条**，按**公众号**和**时间**缩小范围。

现状约束：

| 项 | 现状 |
|----|------|
| 列表 API | `GET /admin/articles?limit=100`，无筛选参数 |
| 前端 | 一次拉取最多 100 条，`applyFilter()` 仅 keyword |
| 时间字段 | `publish_time` 大量为 NULL，需 fallback `collected_at` |
| 布局 | 顶栏已 sticky；workspace 内部分区滚动 |

## 目标

- **FR-1**：顶栏下方新增筛选条（filter bar），不随列表滚动消失（与顶栏同区 sticky 或紧邻 sticky）
- **FR-2**：按公众号筛选（单选或多选，见方案）
- **FR-3**：按时间范围筛选（快捷预设 + 可选自定义区间）
- **FR-4**：筛选与关键词搜索可叠加；统计 pill 反映**当前筛选结果**数量
- **FR-5**：无匹配时列表与详情区给出明确空态

## 非目标（本阶段不做）

- 导出 CSV / 批量操作
- 按 org_id、source 筛选（可后续扩展）
- 全文检索

---

## UI 布局

```
┌──────────────────────────────────────────────────────────────────┐
│ [采] 采集阅读台    🔑 Token [加载]     │  共 55 篇 · 覆盖 89%   │  ← 现有 topbar
├──────────────────────────────────────────────────────────────────┤
│ 公众号 [全部 ▾]  时间 [近 7 天 ▾]  依据 [发布时间 ▾]  [清除筛选] │  ← 新增 filter-bar
│ 显示 12 / 55 篇                                                  │
├──────────────────────┬───────────────────────────────────────────┤
│ 文章列表 + 关键词    │  正文预览 / 纯文本 / 元数据                │
└──────────────────────┴───────────────────────────────────────────┘
```

### 筛选条控件

| 控件 | 类型 | 选项 |
|------|------|------|
| 公众号 | `<select>` 或 searchable dropdown | 「全部」+ 从已加载列表 dedupe 的 `account_name` |
| 时间范围 | `<select>` | 全部 / 今天 / 近 7 天 / 近 30 天 / 近 90 天 / 自定义 |
| 自定义日期 | 两个 `<input type="date">` | 选「自定义」时显示 |
| 时间依据 | `<select>` | 发布时间（缺省回退采集时间）/ 仅采集时间 |
| 清除 | 按钮 | 重置公众号 + 时间 + 自定义日期 |

左侧列表内**保留**关键词搜索，与筛选条 AND 组合。

---

## 筛选逻辑（前端 Phase 1）

```javascript
function articleTime(article, field) {
  if (field === 'collected') return article.collected_at;
  return article.publish_time || article.collected_at; // 发布优先，NULL 回退
}

function inRange(iso, preset, customFrom, customTo) { ... }

function applyAllFilters() {
  filteredArticles = articles.filter(a =>
    matchAccount(a) &&
    matchTime(a) &&
    matchKeyword(a)
  );
}
```

### 时间预设定义（相对「今天」本地日界）

| 预设 | 区间 |
|------|------|
| 全部 | 不限制 |
| 今天 | `[today 00:00, now]` |
| 近 7 天 | `[today-6d 00:00, now]` |
| 近 30 天 | `[today-29d 00:00, now]` |
| 近 90 天 | `[today-89d 00:00, now]` |
| 自定义 | `[from 00:00, to 23:59:59]` |

### 公众号筛选

- **MVP 推荐：单选 dropdown**（实现简单，55 篇规模足够）
- 若账号 > 20：升级为带搜索的下拉（仍纯前端）
- 选项排序：按该号文章数量降序

### 交互细节

- 变更任一筛选项 → 立即过滤列表（debounce 仅用于 keyword）
- 若当前选中文章被筛掉 → 自动选中过滤结果第一篇，或清空详情
- filter 状态写入 `sessionStorage`（与 token 类似），刷新后恢复
- 统计：`显示 N / M 篇`（N=筛选后，M=已加载总数）

---

## 后端扩展（Phase 2，文章量 >100 时）

当 `articles` 表超过单次 limit 时，改为服务端筛选 + 分页。

### API

```
GET /admin/articles
  ?limit=50
  &offset=0
  &account_name=199IT互联网数据中心   # 可选，精确匹配
  &time_field=publish|collected        # 默认 publish（含 fallback 需在 SQL 表达）
  &since=2026-06-01T00:00:00           # 可选 ISO
  &until=2026-06-28T23:59:59           # 可选 ISO
```

```
GET /admin/articles/accounts            # 可选：返回 distinct account_name + count
```

### Service

`article_service.list_articles()` 增加可选 filter 参数；`publish_time` fallback 可用 SQL：

```sql
COALESCE(publish_time, collected_at) BETWEEN :since AND :until
```

### Schema

`ArticleListItem` 不变；路由层透传 query params。

---

## 实现步骤

### Step 1 — 仅前端 MVP（推荐先做）

1. `admin.html`：在 `</header>` 与 `.workspace` 之间插入 `.filter-bar` HTML + CSS
2. 扩展 `applyFilter()` → `applyAllFilters()`，合并公众号 / 时间 / 关键词
3. `loadArticles()` 成功后填充公众号 dropdown
4. 更新 `setStats()` 或在 filter-bar 显示 `N / M`
5. 空态：列表「无匹配文章」；详情提示「请调整筛选条件」

**预估改动**：仅 `wechat_collector/api/static/admin.html`（~120 行）

### Step 2 — API + Service（按需）

1. `article_service.list_articles` 加 filter
2. `admin.py` 加 query params
3. 前端 `loadArticles` 带 query 重新请求（筛选变更时 debounce 300ms）
4. 单测：`tests/test_api.py::test_admin_list_articles_filter`

**预估改动**：3 文件 + 测试

---

## 验收标准

- **AC-1**：选某公众号后，列表只显示该号文章
- **AC-2**：选「近 7 天」后，超出范围文章不显示
- **AC-3**：`publish_time` 为空的文章，在「发布时间」模式下按 `collected_at` 参与筛选
- **AC-4**：筛选 + 关键词可同时生效
- **AC-5**：顶栏滚动时 filter-bar 与 topbar 保持可见（sticky 行为一致）
- **AC-6**：清除筛选恢复全部已加载文章

---

## 风险与说明

| 风险 | 缓解 |
|------|------|
| 只加载 100 条，筛选结果不完整 | Phase 1 在 filter-bar 注明「基于已加载 N 篇」；Phase 2 服务端筛选 |
| `publish_time` 大量 NULL | 默认「发布时间」模式用 collected_at fallback，UI 文案说明 |
| 公众号名不一致（同号不同写法） | 长期靠 org/account 表关联；短期按字符串 exact match |

---

## 建议决策（待你确认）

1. **公众号单选 vs 多选**：建议 MVP **单选**，够用且 UI 简洁
2. **时间默认预设**：建议默认 **近 30 天** 还是 **全部**？（Pilot 阶段建议 **全部**，避免误筛空）
3. **Phase 1 是否足够**：当前 ~55 篇，**仅前端 MVP 即可**；超过 100 篇再上 Phase 2

---

## Todos

- [ ] filter-bar HTML/CSS（sticky、与 topbar 视觉统一）
- [ ] applyAllFilters + 公众号 dropdown 填充
- [ ] 时间预设 + 自定义日期 + 时间依据
- [ ] 统计 N/M + 空态 + sessionStorage 持久化
- [ ] （可选 Phase 2）API query params + service 层筛选
