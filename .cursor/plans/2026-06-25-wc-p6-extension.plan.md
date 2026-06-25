# P6 Chrome 采集插件

Plan-Id: 2026-06-25-wc-p6-extension
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: P4, P5
阶段: 一/二 | 难度: ⭐⭐⭐

## 目标
在真实浏览器环境采集微信文章正文并回传服务端，降低服务端直连风控压力（方案 §4.4 / §7.1）。

## 交付物（Chrome MV3，目录 `extension/`）
- `manifest.json`（MV3，host_permissions: `*://mp.weixin.qq.com/*`）。
- `content.js`：在文章页提取字段（与 P5 选择器一致，前端轻量版）→ 发给 background。
- `background.js`（service worker）：
  - 阶段一：接收「采集当前文章」→ POST `/api/articles`。
  - 阶段二：轮询 `/api/crawl/tasks/next` → 自动开标签页 → 采集 → 回传 → `success/failed`。
- `options.html/js`：配置 API base URL、API Token、采集频率/并发（Token 不写死，方案 §8.3）。
- `popup.html/js`：手动「采集当前文章」「开始/停止自动采集」。
- 风控保护（方案 §6.3）：单标签页串行、单账号频率限制、遇验证码/403 自动停。

## 分期
- **M1（阶段一）**：手动采集当前文章 + 回传。即可参与最小闭环验收。
- **M2（阶段二）**：自动拉任务 + 批量打开 + 失败上报 + 指数退避（与 P8 调度配合）。

## 验收
- [x] M1：content script + popup 手动采集 → `POST /api/articles`
- [x] M2：background 轮询任务 + 开标签页采集 + success/failed 回报
- [x] options 配置 API Token（不写死在代码）
- [x] 风控：串行任务、间隔延迟、验证码/环境异常检测

## 完成提交
`/commit @extension --spec=.cursor/plans/2026-06-25-wc-p6-extension.plan.md`
