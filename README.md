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

## 使用方法

### 基本使用

1. 运行爬虫程序：
   ```bash
   python crawler.py
   ```
2. 输入要爬取的网页URL
3. 程序会自动将内容保存为Markdown文件，并下载相关图片

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

- 通用网站：自动识别主要内容
- 知乎：优化了内容提取和反爬处理
- 可通过修改`SITE_CONFIGS`配置支持更多特定网站

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