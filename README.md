# BasicWebCrawler

一个简单但功能强大的网页爬虫工具，可以将网页内容转换为Markdown格式，并自动下载和保存图片。特别优化了对知乎等特定网站的支持。

## 功能特点

- 将网页内容转换为Markdown格式
- 自动下载和本地化图片资源
- 智能提取网页主要内容
- 支持网站特定的爬取配置
- 支持需要登录的网站（通过cookies）
- 自动处理相对路径和绝对路径的图片URL
- 智能过滤广告和无关内容
- 支持自定义图片保存目录
- **自动从文本中提取URL并批量爬取**
- **支持B站、知乎、AI Base等多个平台**
- **🚀 新增：基于FastMCP的MCP服务器支持**
- **🤖 AI助手集成：可通过Claude Desktop、Cursor等AI工具直接调用**

## 项目结构

```
BasicWebCrawler/
├── crawler.py                      # 核心爬虫模块，包含网页抓取和转换功能
├── cookie_helper.py                # Cookie获取助手，用于需要登录的网站
├── requirements.txt                # Python依赖包列表
├── README.md                       # 项目说明文档
├── zhihu_cookies.json             # 知乎网站的cookies文件（自动生成）
├── assets/                        # 文档资源文件夹
│   └── image.png                  # 说明图片
├── mcp_server/                    # MCP服务器模块
│   ├── mcp_server.py              # 核心MCP服务器实现，提供AI助手集成
│   ├── start_mcp_server.py        # 统一启动脚本，支持多传输方式和依赖检查
│   ├── debug_mcp.py               # MCP服务器调试脚本，用于功能测试
│   └── MCP_USAGE_EXAMPLES.md      # MCP使用示例和详细说明文档
└── tests/                         # 测试模块
    ├── __init__.py                # 测试包初始化文件
    ├── test_url_extraction.py     # URL提取功能测试
    ├── test_site_configs.py       # 网站配置测试
    └── test_mcp_server.py          # MCP服务器完整功能测试
```

### 核心文件说明

- **crawler.py** - 主要爬虫逻辑，包含网页内容提取、图片下载、Markdown转换等核心功能
- **cookie_helper.py** - 辅助工具，帮助用户获取和管理网站cookies，特别适用于需要登录的网站
- **mcp_server/mcp_server.py** - 基于FastMCP的服务器实现，提供5个工具、1个资源、2个提示模板
- **mcp_server/start_mcp_server.py** - 统一启动脚本，集成依赖检查、多传输方式支持、配置示例显示
- **mcp_server/debug_mcp.py** - 开发调试工具，用于测试MCP服务器各项功能是否正常
- **mcp_server/MCP_USAGE_EXAMPLES.md** - 详细的MCP使用文档，包含配置方法和使用示例
- **tests/test_mcp_server.py** - 全面的MCP服务器测试套件，验证所有工具和功能

## 安装要求

- Python 3.8+
- 依赖包：
  ```
  requests
  beautifulsoup4
  markdownify
  fastmcp  # MCP服务器支持
  ```

## 安装步骤

1. 克隆项目到本地
2. 安装依赖：
   ```bash
   pip install requests beautifulsoup4 markdownify fastmcp
   ```

## 使用方法

### 🤖 MCP服务器模式（推荐）

MCP服务器模式允许AI助手（如Claude Desktop、Cursor等）直接调用爬虫功能。

#### 启动MCP服务器

MCP服务器支持三种传输方式，每种适用于不同的场景：

##### 🔗 方式一：STDIO 传输（推荐，本地集成）

**特点**：
- 通过标准输入输出通信，无需网络端口
- 延迟最低，最适合本地AI助手集成
- Claude Desktop官方推荐方式

**启动方法**：
```bash
# 方法1：使用统一启动脚本（推荐）
python mcp_server/start_mcp_server.py

# 方法2：使用统一启动脚本 + 命令行参数
python mcp_server/start_mcp_server.py --transport stdio --auto

# 方法3：直接运行Python脚本
python mcp_server/mcp_server.py

# 方法4：使用FastMCP CLI
fastmcp run mcp_server/mcp_server.py
```

##### 🌐 方式二：SSE 传输（Server-Sent Events）

**特点**：
- 基于HTTP的服务器推送事件
- 支持远程访问和多客户端连接
- 适合Web应用和分布式系统

**启动方法**：
```bash
# 方法1：使用统一启动脚本（推荐）
python mcp_server/start_mcp_server.py --transport sse --host 127.0.0.1 --port 8000 --auto

# 方法2：使用FastMCP CLI
fastmcp run mcp_server/mcp_server.py --transport sse --host 127.0.0.1 --port 8000

# 方法3：修改mcp_server.py中的main函数：
# mcp.run(transport="sse", host="127.0.0.1", port=8000)
```

**访问地址**：`http://127.0.0.1:8000/sse`

##### ⚡ 方式三：HTTP 传输（Streamable HTTP）

**特点**：
- 基于HTTP流的双向通信
- 更现代的网络协议支持
- 适合云部署和企业级应用

**启动方法**：
```bash
# 方法1：使用统一启动脚本（推荐）
python mcp_server/start_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --auto

# 方法2：使用FastMCP CLI
fastmcp run mcp_server/mcp_server.py --transport http --host 127.0.0.1 --port 8000

# 方法3：修改mcp_server.py中的main函数：
# mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
```

**访问地址**：`http://127.0.0.1:8000/mcp`

##### 🎯 传输方式选择指南

| 传输方式 | 使用场景 | 优点 | 缺点 | 推荐度 |
|---------|---------|------|------|--------|
| **STDIO** | 本地AI助手集成 | 延迟最低、配置简单、安全性高 | 仅支持本地连接 | ⭐⭐⭐⭐⭐ |
| **SSE** | Web应用、远程访问 | 支持多客户端、可远程访问 | 需要端口、略高延迟 | ⭐⭐⭐⭐ |
| **HTTP** | 云部署、企业应用 | 现代协议、双向通信 | 配置复杂、需要端口 | ⭐⭐⭐ |

**推荐选择**：
- 🏠 **本地使用**：选择 **STDIO** 传输
- 🌐 **远程访问**：选择 **SSE** 传输
- ☁️ **云部署**：选择 **HTTP** 传输

##### 🚀 快速启动示例

```bash
# STDIO 传输（本地AI助手）
python mcp_server/start_mcp_server.py --transport stdio --auto

# SSE 传输（远程访问，端口8000）
python mcp_server/start_mcp_server.py --transport sse --port 8000 --auto

# HTTP 传输（云部署，自定义端口）
python mcp_server/start_mcp_server.py --transport http --host 0.0.0.0 --port 9000 --auto

# 交互式启动（显示配置示例）
python mcp_server/start_mcp_server.py --transport sse --port 8000

# 查看帮助信息
python mcp_server/start_mcp_server.py --help
```

> 💡 **提示**：`start_mcp_server.py` 是统一的启动入口，集成了依赖检查、配置示例显示、多传输方式支持等功能。推荐使用此脚本启动MCP服务器。

#### 配置AI助手

根据选择的传输方式，需要不同的配置方法：

##### 📋 STDIO 传输配置

**Claude Desktop 配置**：

打开 Claude Desktop → Settings → Developer → Edit Config，添加：

```json
{
  "mcpServers": {
    "basic-web-crawler": {
      "command": "python",
      "args": ["D:/myWorks/BasicWebCrawler/mcp_server/mcp_server.py"],
      "cwd": "D:/myWorks/BasicWebCrawler"
    }
  }
}
```

**Cursor 配置**：

在 `~/.cursor/mcp.json` 文件中添加：

```json
{
  "mcpServers": {
    "basic-web-crawler": {
      "command": "python", 
      "args": ["D:/myWorks/BasicWebCrawler/mcp_server/mcp_server.py"],
      "cwd": "D:/myWorks/BasicWebCrawler"
    }
  }
}
```

##### 🌐 SSE/HTTP 传输配置

**Cherry Stuidio 配置**：

```json
{
  "mcpServers": {
    "basic-web-crawler": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

**HTTP 传输配置**：

```json
{
  "mcpServers": {
    "basic-web-crawler": {
      "type": "streamableHttp",
      "url": "http://localhost:9000/mcp"
    }
  }
}
```

**使用 mcp-proxy 转换（SSE转STDIO）**：

如果你的MCP服务器运行在SSE模式，但AI助手只支持STDIO，可以使用 `mcp-proxy`：

```bash
# 安装 mcp-proxy
uv tool install mcp-proxy

# Claude Desktop 配置
{
  "mcpServers": {
      "basic-web-crawler": {
         "command": "mcp-proxy",
         "args": ["http://127.0.0.1:8000/sse"]
      }
   }
}
```

#### MCP工具说明

MCP服务器提供以下工具：

1. **crawl_single_url** - 爬取单个网页
   - 参数：url, img_folder, use_cookies, cookies_file
   - 功能：爬取指定URL并转换为Markdown

2. **crawl_urls_from_text** - 批量爬取URL
   - 参数：text, img_folder, use_cookies, cookies_file
   - 功能：从文本中提取URL并批量爬取

3. **extract_urls** - 提取URL列表
   - 参数：text
   - 功能：从文本中提取所有有效URL

4. **check_site_config** - 检查网站配置
   - 参数：url
   - 功能：查看特定网站的爬取配置信息

5. **get_supported_sites** - 获取支持的网站
   - 功能：列出所有预配置的网站

#### MCP资源

- **crawler://config** - 爬虫配置信息（JSON格式）

#### MCP提示模板

- **crawl_webpage_prompt** - 爬取网页的标准提示
- **batch_crawl_prompt** - 批量爬取的标准提示

#### AI助手使用示例

在AI助手中，你可以这样使用：

```
请帮我爬取这个网页的内容：https://www.example.com
```

```
我有一段包含多个URL的文本，请帮我批量爬取：
这里有一些有趣的链接：
https://www.github.com
https://www.stackoverflow.com
```

### 📱 命令行模式

#### 基本使用

1. 运行爬虫程序：
   ```bash
   python crawler.py
   ```
2. 选择运行模式：
   - 模式1：直接爬取单个URL
   - 模式2：从文本中提取URL并批量爬取
3. 根据提示输入内容
4. 程序会自动将内容保存为Markdown文件，并下载相关图片

#### 从文本中提取URL并批量爬取

1. 运行爬虫程序并选择模式2：
   ```bash
   python crawler.py
   # 然后选择"2"
   ```
2. 输入包含URL的文本，每行输入完成后按回车
3. 输入完成后按Ctrl+Z（Windows）或Ctrl+D结束输入
4. 程序会自动从文本中提取URL，并依次爬取每个URL的内容
5. 最终生成一个包含所有爬取结果的合并Markdown文件

示例文本输入格式:
```
这是一个介绍文章，里面有几个链接：https://www.example.com 和 https://blog.example.org
还有一些其他网站 www.another-example.net
```

#### 爬取需要登录的网站（如知乎）

1. 首先运行cookie助手获取cookies：
   ```bash
   python cookie_helper.py
   ```

2. 按照提示获取cookies：
   - 使用Chrome浏览器登录目标网站
   - 按F12打开开发者工具
   - 切换到"Network"(网络)标签
   - 刷新页面
   - 在请求列表中找到主域名请求
   - 在Headers中找到"Cookie:"开头的行
   - 复制完整的cookie值

   参考下图：![image](assets\image.png)

3. 将复制的cookies粘贴到程序中，它会自动生成`zhihu_cookies.json`文件

4. 运行爬虫程序并使用cookies文件：
   ```bash
   python crawler.py
   ```

## 测试

项目包含完整的单元测试，确保功能的稳定性和可靠性。

### 运行测试

运行所有测试：
```bash
python -m unittest discover tests
```

运行特定测试：
```bash
# 测试URL提取功能
python -m unittest tests.test_url_extraction

# 测试网站配置功能
python -m unittest tests.test_site_configs
```

### 测试MCP服务器

测试MCP服务器功能：
```bash
python test_mcp_server.py
```

### 测试覆盖

- **URL提取测试**：验证从文本中提取URL的准确性
- **批量爬取测试**：测试批量处理多个URL的功能
- **网站配置测试**：确保各网站特定配置的正确性
- **URL清理测试**：验证URL标点符号清理功能
- **MCP服务器测试**：验证MCP工具、资源和提示的正确性

## 输出说明

- Markdown文件：保存在运行目录下，文件名格式为`{页面标题}_{时间戳}.md`
- 图片文件：保存在`./images/`目录下，使用MD5哈希值作为文件名

## 支持的网站

- **通用网站**：自动识别主要内容区域
- **知乎 (zhihu.com)**：优化了内容提取和反爬处理，支持cookies认证
- **哔哩哔哩 (bilibili.com)**：针对视频页面优化的内容选择器
- **AI Base (aibase.com)**：专门针对AI工具页面的内容提取
- **可扩展**：通过修改`SITE_CONFIGS`配置支持更多特定网站

### 网站配置示例

每个网站都有专门的配置，包括：
- 特定的HTTP请求头
- 针对性的内容选择器
- Cookie需求设置

## MCP服务器架构

MCP服务器基于FastMCP框架构建，提供以下特性：

- **工具(Tools)**：可执行的爬虫功能
- **资源(Resources)**：配置信息和元数据
- **提示(Prompts)**：标准化的交互模板
- **异步支持**：高性能的并发处理
- **类型安全**：完整的类型注解和验证

### 部署选项

1. **本地部署**：直接运行Python脚本
2. **容器部署**：使用Docker容器化部署
3. **云服务**：部署到云平台提供API服务

## 注意事项

1. 对于需要登录的网站，cookies可能会定期失效，需要重新获取
2. 部分网站可能有反爬虫机制，建议控制爬取频率
3. 图片下载可能受网络条件影响
4. 确保有足够的磁盘空间存储图片
5. MCP服务器需要保持运行状态以供AI助手调用

## 自定义配置

可以通过修改`crawler.py`中的`SITE_CONFIGS`字典来添加新的网站配置：

```python
SITE_CONFIGS = {
    'example.com': {
        'headers': {
            'Referer': 'https://example.com',
            # 其他请求头
        },
        'main_content_selectors': ['.article', '#main-content'],
        'needs_cookies': False
    }
}
```

## 常见问题

1. **403错误**
   - 检查cookies是否有效
   - 确认是否需要登录
   - 检查网站是否有反爬虫机制

2. **图片下载失败**
   - 检查网络连接
   - 确认图片URL是否有效
   - 检查是否有足够的存储空间

3. **内容提取不完整**
   - 可能需要调整内容选择器
   - 检查网页结构是否符合预期

4. **MCP服务器连接失败**
   - 确认服务器正在运行
   - 检查配置文件路径是否正确
   - 验证Python环境和依赖是否安装

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。在提交代码前，请确保：

1. 代码符合Python代码规范
2. 添加了必要的注释
3. 更新了相关文档
4. 通过了所有测试

## 许可证

MIT License