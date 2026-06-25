# Chrome 采集插件（P6）

Manifest V3 插件，在真实浏览器环境中采集微信公众号文章并回传 `wechat_collector` API。

## 功能

- **M1 手动采集**：在微信文章页点击扩展 →「采集当前文章」→ `POST /api/articles`
- **M2 自动采集**：轮询 `GET /api/crawl/tasks/next`，打开标签页采集后标记 success/failed
- **风控**：单任务串行、任务间隔可配置、识别验证码/环境异常页并可选自动停采

## 安装（开发者模式）

1. 启动采集 API：
   ```bash
   export COLLECTOR_API_TOKEN=your-token
   uvicorn wechat_collector.api.app:app --reload --port 8787
   ```
2. Chrome 打开 `chrome://extensions/`
3. 开启「开发者模式」→「加载已解压的扩展程序」
4. 选择本仓库的 `extension/` 目录
5. 打开扩展「选项」，填写：
   - API Base URL：`http://127.0.0.1:8787`
   - API Token：与 `COLLECTOR_API_TOKEN` 一致

## 使用

### 手动采集（M1）

1. 浏览器打开任意 `mp.weixin.qq.com/s/...` 文章
2. 点击扩展图标 →「采集当前文章」
3. 在 `http://127.0.0.1:8787/admin` 或 `/admin/articles` 查看入库结果

### 自动采集（M2）

1. 先通过 API 或导入脚本往候选池写入 `pending` 任务
2. 扩展弹窗点击「开始自动采集」
3. 插件按间隔拉任务、开标签页、解析、入库并回报状态

## 目录结构

```
extension/
  manifest.json       # MV3 清单
  background.js       # Service Worker：API 调用、自动队列
  content.js          # 页面内采集入口
  popup.*             # 弹窗 UI
  options.*           # 配置页（Token 不写死在代码里）
  lib/
    parser.js         # 与 P5 选择器对齐的 DOM 解析
    api.js            # 采集 API 客户端
    storage.js        # chrome.storage.sync 配置
```

## 调试

- Service Worker 日志：`chrome://extensions/` → 扩展详情 → Service Worker
- 内容脚本：文章页 DevTools Console
- 若 API 在非 localhost，确保 `manifest.json` 的 `host_permissions` 覆盖你的服务地址
