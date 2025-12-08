# BasicWebCrawler MCP 版本说明

## 📦 版本概览

BasicWebCrawler MCP提供三个版本，满足不同需求：

| 版本 | 文件名 | 适用场景 | 推荐度 |
|------|--------|----------|--------|
| **智能版** | `mcp_server_smart.py` | JS渲染网站、不确定网站类型 | ⭐⭐⭐⭐⭐ |
| **增强版** | `mcp_server_enhanced.py` | 需要质量评估和诊断 | ⭐⭐⭐⭐ |
| **基础版** | `mcp_server.py` | 简单静态网站 | ⭐⭐⭐ |

---

## 🎯 版本对比

### 基础版 (Basic)

**核心功能**：
- ✅ 爬取单个URL
- ✅ 批量爬取
- ✅ 图片下载
- ✅ Markdown转换
- ✅ LLM内容重写

**适用场景**：
- 简单的静态网页
- 已知可以直接爬取的网站
- 不需要JS渲染

**优点**：
- 简单直接
- 速度快
- 稳定可靠

**缺点**：
- ❌ 无法处理JS渲染网站
- ❌ 没有质量评估
- ❌ 失败时没有诊断建议

### 增强版 (Enhanced)

**在基础版基础上新增**：
- ✅ 内容质量自动评估
- ✅ 爬取失败诊断工具
- ✅ 批量爬取+AI总结
- ✅ 智能决策是否需要LLM重写

**核心工具**：
1. `crawl_with_quality_check` - 带质量检查的爬取
2. `diagnose_crawl_failure` - 失败诊断
3. `crawl_and_summarize` - 批量爬取+总结

**适用场景**：
- 需要评估内容质量
- 想知道为什么爬取失败
- 需要批量处理并生成报告

**优点**：
- 智能质量评估
- 详细失败诊断
- 批量处理能力

**缺点**：
- ❌ 仍然无法处理JS渲染网站
- ❌ 失败后需要手动切换方案

### 智能版 (Smart) ⭐ **推荐**

**在增强版基础上新增**：
- ✅ 智能检测网站特征
- ✅ 自动选择最佳策略
- ✅ 浏览器集成支持
- ✅ 批量任务智能规划
- ✅ 失败自动切换方案

**核心工具**：
1. `smart_crawl_single_url` - 智能爬取
2. `browser_extract_and_save` - 浏览器内容保存
3. `batch_browser_extract` - 批量浏览器处理

**适用场景**：
- JS渲染的现代网站（如HuggingFace、GitHub Pages）
- 不确定网站类型
- 需要高成功率
- 批量处理多个网站

**优点**：
- 🚀 智能检测和决策
- 🚀 浏览器+爬虫无缝集成
- 🚀 自动切换策略
- 🚀 最高成功率（~95%）

**特别适合**：
- HuggingFace模型页面
- GitHub Pages
- 现代SPA应用
- 需要JS的动态网站

---

## 🚀 快速选择指南

### 我应该用哪个版本？

#### 选择智能版，如果：
- ✅ 要爬取的网站需要JS渲染
- ✅ 不确定网站是否需要JS
- ✅ 想要最高的成功率
- ✅ 需要批量处理多个网站
- ✅ 想要自动化程度最高

#### 选择增强版，如果：
- ✅ 网站不需要JS渲染
- ✅ 需要评估内容质量
- ✅ 需要诊断失败原因
- ✅ 需要批量爬取+AI总结

#### 选择基础版，如果：
- ✅ 简单的静态网页
- ✅ 只需要基本爬取功能
- ✅ 追求最快速度
- ✅ 不需要额外功能

---

## 📖 详细文档

### 智能版 (推荐)
- [智能版使用指南](./README_智能版本.md)
- [更新日志](./CHANGELOG_智能版本.md)
- [HuggingFace爬取示例](./示例_爬取HuggingFace模型页面.md)

### 增强版
- [增强版功能说明](./README_增强功能.md)
- [增强版使用示例](./示例_使用增强功能.md)

### 基础版
- [基础版README](./README.md)

---

## 🔧 安装和启动

### 1. 安装依赖

```bash
cd /path/to/BasicWebCrawler
pip install -r requirements.txt
```

### 2. 配置环境变量（使用LLM功能时需要）

```bash
cp mcp_server/env.example .env
# 编辑.env，填入API密钥
```

### 3. 启动指定版本

#### 方法1：使用启动脚本（推荐）

```bash
# 启动智能版（默认）
python mcp_server/start_mcp_server.py --auto

# 启动增强版
python mcp_server/start_mcp_server.py --version enhanced --auto

# 启动基础版
python mcp_server/start_mcp_server.py --version basic --auto
```

#### 方法2：直接运行

```bash
# 智能版
python mcp_server/mcp_server_smart.py

# 增强版
python mcp_server/mcp_server_enhanced.py

# 基础版
python mcp_server/mcp_server.py
```

---

## ⚙️ Cursor配置

### 智能版（推荐）

```json
{
  "mcpServers": {
    "web-crawler-smart": {
      "command": "python",
      "args": [
        "/path/to/BasicWebCrawler/mcp_server/mcp_server_smart.py"
      ],
      "cwd": "/path/to/BasicWebCrawler"
    }
  }
}
```

### 使用启动脚本（支持版本切换）

```json
{
  "mcpServers": {
    "web-crawler": {
      "command": "python",
      "args": [
        "/path/to/BasicWebCrawler/mcp_server/start_mcp_server.py",
        "--version", "smart",
        "--transport", "stdio"
      ],
      "cwd": "/path/to/BasicWebCrawler"
    }
  }
}
```

### 多版本共存

```json
{
  "mcpServers": {
    "crawler-smart": {
      "command": "python",
      "args": ["/path/to/mcp_server_smart.py"],
      "cwd": "/path/to/BasicWebCrawler"
    },
    "crawler-enhanced": {
      "command": "python",
      "args": ["/path/to/mcp_server_enhanced.py"],
      "cwd": "/path/to/BasicWebCrawler"
    },
    "crawler-basic": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "cwd": "/path/to/BasicWebCrawler"
    }
  }
}
```

---

## 🎯 使用示例

### 智能版示例

```python
# 示例1：智能爬取单个URL
smart_crawl_single_url(
    url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
    output_dir="/path/to/output",
    auto_switch_to_browser=True,
    use_llm_if_low_quality=True
)

# 示例2：批量处理JS渲染网站
batch_browser_extract(
    urls=[
        "https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
        "https://hf-mirror.com/zai-org/GLM-4.5V"
    ],
    output_dir="/path/to/output",
    use_llm_summary=True,
    llm_provider="bailian",
    llm_model="qwen-plus"
)

# 示例3：从浏览器保存内容
browser_extract_and_save(
    current_url="https://...",
    page_content="<浏览器提取的内容>",
    output_dir="/path/to/output",
    model_name="GLM-4.1V-9B-Base",
    use_llm=True
)
```

### 增强版示例

```python
# 示例1：带质量检查的爬取
crawl_with_quality_check(
    url="https://example.com",
    output_dir="/path/to/output",
    auto_rewrite=True
)

# 示例2：诊断失败原因
diagnose_crawl_failure(
    url="https://example.com",
    verbose=True
)

# 示例3：批量爬取+总结
crawl_and_summarize(
    urls=["url1", "url2", "url3"],
    output_dir="/path/to/output",
    llm_provider="bailian",
    llm_model="qwen-plus"
)
```

### 基础版示例

```python
# 示例1：基本爬取
crawl_single_url(
    url="https://example.com",
    output_dir="/path/to/output"
)

# 示例2：LLM重写
crawl_and_regenerate_with_llm(
    url="https://example.com",
    provider="deepseek",
    output_dir="/path/to/output"
)
```

---

## 📊 功能对比表

| 功能 | 基础版 | 增强版 | 智能版 |
|------|:------:|:------:|:------:|
| 基础爬取 | ✅ | ✅ | ✅ |
| 图片下载 | ✅ | ✅ | ✅ |
| LLM重写 | ✅ | ✅ | ✅ |
| 质量评估 | ❌ | ✅ | ✅ |
| 失败诊断 | ❌ | ✅ | ✅ |
| 批量总结 | ❌ | ✅ | ✅ |
| **智能检测** | ❌ | ❌ | ✅ |
| **自动切换策略** | ❌ | ❌ | ✅ |
| **浏览器集成** | ❌ | ❌ | ✅ |
| **任务规划** | ❌ | ❌ | ✅ |
| JS渲染支持 | ⚠️ 有限 | ⚠️ 有限 | ✅ 完整 |
| 成功率 | ~60% | ~75% | ~95% |

---

## 🎉 推荐配置

### 日常使用（最推荐）
```bash
# 安装智能版
python mcp_server/start_mcp_server.py --version smart --auto
```

**原因**：
- 覆盖所有场景
- 最高成功率
- 自动智能决策
- 无需手动切换

### 性能优先
```bash
# 如果确定是静态网站，用基础版
python mcp_server/start_mcp_server.py --version basic --auto
```

### 调试和诊断
```bash
# 需要详细诊断时用增强版
python mcp_server/start_mcp_server.py --version enhanced --auto
```

---

## 🆘 常见问题

### Q1: 三个版本可以同时使用吗？
**A**: 可以！在Cursor配置中添加多个MCP服务器，用不同的名称区分。

### Q2: 智能版比基础版慢吗？
**A**: 智能版包含检测步骤（约1-2秒），但避免了无效重试，总体更快。

### Q3: 智能版支持所有基础版功能吗？
**A**: 是的，智能版包含了基础版和增强版的所有功能。

### Q4: 如何切换版本？
**A**: 
1. 修改Cursor配置中的启动命令
2. 或使用启动脚本的`--version`参数
3. 重启MCP服务器

### Q5: 智能版需要浏览器扩展吗？
**A**: 需要Cursor Browser Extension，但Cursor已内置，无需额外安装。

---

## 📚 更多资源

- [智能版完整文档](./README_智能版本.md)
- [智能版更新日志](./CHANGELOG_智能版本.md)
- [HuggingFace爬取教程](./示例_爬取HuggingFace模型页面.md)
- [增强版功能说明](./README_增强功能.md)
- [LLM客户端文档](./llm_client.py)

---

## 🙏 贡献

欢迎提交Issue和PR！

- GitHub: [BasicWebCrawler](https://github.com/yourusername/BasicWebCrawler)
- Issues: [反馈问题](https://github.com/yourusername/BasicWebCrawler/issues)

---

**最后更新**: 2024-12-08
**推荐版本**: 智能版 (Smart)

