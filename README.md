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

```bash
# 直接运行MCP服务器
python mcp_server.py

# 或使用FastMCP CLI
fastmcp run mcp_server.py
```

#### 配置AI助手

**对于Claude Desktop：**

在Claude Desktop的配置文件中添加：

```json
{
  "mcpServers": {
    "basic-web-crawler": {
      "command": "python",
      "args": ["D:/myWorks/BasicWebCrawler/mcp_server.py"],
      "cwd": "D:/myWorks/BasicWebCrawler"
    }
  }
}
```

**对于Cursor：**

在 `~/.cursor/mcp.json` 文件中添加：

```json
{
  "mcpServers": {
    "basic-web-crawler": {
      "command": "python",
      "args": ["D:/myWorks/BasicWebCrawler/mcp_server.py"],
      "cwd": "D:/myWorks/BasicWebCrawler"
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