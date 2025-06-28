# BasicWebCrawler MCP服务器使用示例

本文档提供了如何在不同AI助手中使用BasicWebCrawler MCP服务器的详细示例。

## 🚀 快速开始

### 1. 启动MCP服务器

```bash
# 使用启动脚本（推荐）
python start_mcp_server.py

# 或直接启动
python mcp_server.py

# 或使用FastMCP CLI
fastmcp run mcp_server.py
```

### 2. 配置AI助手

将MCP服务器添加到你的AI助手配置中（详见README.md）。

## 📖 使用示例

### 单个网页爬取

**用户提问：**
```
请帮我爬取这个网页的内容：https://www.github.com/microsoft/vscode
```

**AI助手会：**
1. 调用 `crawl_single_url` 工具
2. 爬取GitHub页面内容
3. 转换为Markdown格式
4. 下载并本地化图片
5. 返回爬取结果和文件路径

### 批量URL爬取

**用户提问：**
```
我有一段包含多个URL的文本，请帮我批量爬取：

今天看到几个有趣的网站：
- GitHub的VS Code项目：https://github.com/microsoft/vscode
- Stack Overflow的Python标签：https://stackoverflow.com/questions/tagged/python
- 还有这个AI工具网站：https://www.aibase.com

请帮我爬取这些网站的内容。
```

**AI助手会：**
1. 调用 `extract_urls` 工具提取URL
2. 调用 `crawl_urls_from_text` 工具批量爬取
3. 合并所有内容到一个Markdown文件
4. 提供详细的爬取统计

### URL提取和分析

**用户提问：**
```
请从这段文本中提取所有的URL，并告诉我哪些网站需要特殊配置：

我最近在研究这些网站：
- https://www.zhihu.com/question/12345
- https://www.bilibili.com/video/BV1234567890
- https://www.example.com
- www.google.com
```

**AI助手会：**
1. 调用 `extract_urls` 工具
2. 显示提取到的URL列表
3. 标识哪些网站需要cookies
4. 提供网站配置信息

### 网站配置检查

**用户提问：**
```
请检查知乎网站的爬取配置
```

**AI助手会：**
1. 调用 `check_site_config` 工具
2. 显示知乎的特定配置
3. 说明是否需要cookies
4. 列出内容选择器和请求头

### 获取支持的网站列表

**用户提问：**
```
这个爬虫支持哪些网站？
```

**AI助手会：**
1. 调用 `get_supported_sites` 工具
2. 列出所有预配置的网站
3. 显示每个网站的配置特点
4. 提供使用建议

## 🔧 高级用法

### 使用Cookies爬取需要登录的网站

**用户提问：**
```
请使用cookies文件爬取这个知乎问题：https://www.zhihu.com/question/12345
cookies文件路径是：./zhihu_cookies.json
```

**AI助手会：**
1. 检查网站配置，发现需要cookies
2. 使用提供的cookies文件
3. 调用 `crawl_single_url` 工具，传入cookies参数
4. 成功爬取需要登录的内容

### 自定义图片保存目录

**用户提问：**
```
请爬取这个网页，并将图片保存到 ./downloads/images/ 目录：
https://www.example.com
```

**AI助手会：**
1. 调用 `crawl_single_url` 工具
2. 设置 `img_folder` 参数为 `./downloads/images/`
3. 将图片下载到指定目录

## 📊 实际应用场景

### 场景1：技术文档收集

```
我正在研究FastMCP框架，请帮我爬取以下文档页面：
- https://gofastmcp.com/getting-started/quickstart
- https://gofastmcp.com/servers/core-components
- https://gofastmcp.com/clients/client

请将所有内容合并到一个文档中，方便我离线阅读。
```

### 场景2：竞品分析

```
请帮我爬取这些AI工具网站的介绍页面：
https://www.aibase.com/tool/chatgpt
https://www.aibase.com/tool/claude
https://www.aibase.com/tool/gemini

我需要分析它们的功能特点。
```

### 场景3：新闻文章收集

```
这里有几篇关于AI发展的文章，请帮我爬取内容：

1. https://example-news.com/ai-breakthrough-2024
2. https://tech-blog.com/future-of-ai
3. https://research-paper.com/ai-trends

请保存为Markdown格式，我要做研究笔记。
```

## 🛠️ 故障排除

### 常见问题和解决方案

1. **MCP服务器无法连接**
   ```
   MCP服务器连接失败，请检查服务器是否正在运行
   ```
   - 确认MCP服务器正在运行
   - 检查AI助手配置文件路径
   - 验证Python环境

2. **爬取失败**
   ```
   爬取失败：403 Forbidden
   ```
   - 检查是否需要cookies
   - 使用 `check_site_config` 工具查看网站配置
   - 考虑添加适当的请求头

3. **图片下载失败**
   ```
   部分图片下载失败
   ```
   - 检查网络连接
   - 确认图片URL有效性
   - 检查磁盘空间

## 💡 最佳实践

1. **批量爬取时**：
   - 控制爬取频率，避免对目标网站造成压力
   - 使用合适的图片保存目录
   - 定期清理下载的文件

2. **使用Cookies时**：
   - 定期更新cookies文件
   - 确保cookies文件安全存储
   - 不要在公共环境中使用包含敏感信息的cookies

3. **配置AI助手时**：
   - 使用绝对路径避免路径问题
   - 确保Python环境正确配置
   - 定期更新依赖包

## 🔗 相关资源

- [FastMCP官方文档](https://gofastmcp.com/)
- [Model Context Protocol规范](https://modelcontextprotocol.io/)
- [项目GitHub仓库](https://github.com/your-username/BasicWebCrawler)
- [问题反馈和建议](https://github.com/your-username/BasicWebCrawler/issues) 