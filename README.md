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

## 安装要求

- Python 3.8+
- 依赖包：
  ```
  requests
  beautifulsoup4
  markdownify
  ```

## 安装步骤

1. 克隆项目到本地
2. 安装依赖：
   ```bash
   pip install requests beautifulsoup4 markdownify
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

### 测试覆盖

- **URL提取测试**：验证从文本中提取URL的准确性
- **批量爬取测试**：测试批量处理多个URL的功能
- **网站配置测试**：确保各网站特定配置的正确性
- **URL清理测试**：验证URL标点符号清理功能

## 使用方法

### 基本使用

1. 运行爬虫程序：
   ```bash
   python crawler.py
   ```
2. 选择运行模式：
   - 模式1：直接爬取单个URL
   - 模式2：从文本中提取URL并批量爬取
3. 根据提示输入内容
4. 程序会自动将内容保存为Markdown文件，并下载相关图片

### 从文本中提取URL并批量爬取

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

### 爬取需要登录的网站（如知乎）

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

## 注意事项

1. 对于需要登录的网站，cookies可能会定期失效，需要重新获取
2. 部分网站可能有反爬虫机制，建议控制爬取频率
3. 图片下载可能受网络条件影响
4. 确保有足够的磁盘空间存储图片

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

1. 403错误
   - 检查cookies是否有效
   - 确认是否需要登录
   - 检查网站是否有反爬虫机制

2. 图片下载失败
   - 检查网络连接
   - 确认图片URL是否有效
   - 检查是否有足够的存储空间

3. 内容提取不完整
   - 可能需要调整内容选择器
   - 检查网页结构是否符合预期

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。在提交代码前，请确保：

1. 代码符合Python代码规范
2. 添加了必要的注释
3. 更新了相关文档

## 许可证

MIT License