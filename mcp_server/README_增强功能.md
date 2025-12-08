# BasicWebCrawler MCP 增强功能使用指南

## 📋 概述

本文档介绍 BasicWebCrawler MCP 服务器的增强功能，包括：

1. **智能爬取失败诊断** - 快速定位爬取失败的原因
2. **内容质量自动评估** - 判断爬取内容的可读性
3. **智能大模型重写** - 自动或手动使用大模型优化内容
4. **批量爬取+总结** - 爬取多个URL并生成总结报告

## 🚀 新增工具

### 1. `crawl_with_quality_check` - 带质量检查的爬取

**功能**：爬取网页并自动评估内容质量，可选自动用大模型重写。

**使用场景**：
- 想知道爬取的内容质量如何
- 自动判断是否需要大模型优化
- 一键完成"爬取+评估+重写"流程

**参数**：
```python
crawl_with_quality_check(
    url="https://example.com",
    img_folder="images",              # 图片保存目录
    use_cookies=False,                # 是否使用cookies
    cookies_file=None,                # cookies文件路径
    output_dir=None,                  # 输出目录
    max_retries=2,                    # 最大重试次数
    auto_rewrite=False,               # 是否自动重写
    llm_provider="deepseek",          # 大模型厂商
    llm_model=None,                   # 大模型名称
    verbose=False                     # 是否详细日志
)
```

**示例1：仅评估质量**
```
爬取 https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base 的内容，
并评估质量
```

**示例2：自动重写低质量内容**
```
爬取 https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base，
评估质量，如果质量不佳就用 deepseek 自动重写
```

**输出示例**：
```
✅ 爬取成功！

📄 页面标题: zai-org/GLM-4.1V-9B-Base · HF Mirror
🔗 URL: https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base
📁 保存文件: /path/to/file.md
📊 内容长度: 15234 字符
...

============================================================
📊 内容质量评估
============================================================
• 质量得分: 75/100
• 内容长度: 15234 字符
• 可读性: medium
• 建议重写: 是

发现的问题:
  • 链接密度过高（可能是菜单内容）
  • 段落划分不清晰

💡 提示: 内容质量不佳，建议使用大模型重写
```

---

### 2. `crawl_and_summarize` - 批量爬取+总结

**功能**：爬取多个URL并用大模型生成统一的总结报告。

**使用场景**：
- "爬取 A、B、C 三个网页，然后用 bailian 的 qwen-plus 总结"
- 批量处理多个网页并生成报告
- 需要AI理解多个网页并提炼要点

**参数**：
```python
crawl_and_summarize(
    urls=["url1", "url2", "url3"],    # URL列表
    output_dir="/path/to/output",     # 输出目录（必填）
    llm_provider="bailian",           # 大模型厂商
    llm_model="qwen-plus",            # 模型名称
    summary_prompt=None,              # 自定义总结提示词
    img_folder="images",              # 图片目录
    use_cookies=False,                # 是否使用cookies
    cookies_file=None,                # cookies文件
    save_originals=True               # 是否保存原始内容
)
```

**示例**：
```
帮我爬取以下网页：
1. https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base
2. https://hf-mirror.com/zai-org/GLM-4.1V-9B-Thinking
3. https://hf-mirror.com/zai-org/GLM-4.5V

然后用百炼的 qwen-plus 模型生成一份总结报告，
保存到 /Users/damon/Desktop/中移互联网-品质部AI智能客服
```

**输出**：
- 生成 `总结报告_时间戳.md` - AI生成的总结
- 可选保存每个网页的原始Markdown文件

---

### 3. `diagnose_crawl_failure` - 爬取失败诊断

**功能**：诊断为什么某个网页爬取失败。

**使用场景**：
- 爬取失败但不知道原因
- 想快速了解网站需要什么配置
- 调试爬取问题

**参数**：
```python
diagnose_crawl_failure(
    url="https://example.com",
    verbose=True                      # 详细日志
)
```

**示例**：
```
诊断为什么 https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base 
爬取失败
```

**输出示例**：
```
============================================================
🔍 诊断爬取失败原因: https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base
============================================================

1️⃣ 测试基本连通性...
✓ HTTP状态码: 200
✓ 最终URL: https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base

2️⃣ 检查网站配置...
📋 网站配置 (hf-mirror.com):
  • 需要JS渲染: 是
  • 需要Cookies: 否
  • 内容选择器: 5 个

3️⃣ 分析HTML结构...
📄 HTML分析:
  • 文档长度: 8234 字符
  • 标题: zai-org/GLM-4.1V-9B-Base · HF Mirror
  ⚠️ 检测到SPA特征（#app/#root/vite），需要JS渲染
     - #app存在: True
     - #root存在: False
     - Vite标识: False

🎯 内容选择器匹配:
  ✓ .model-card-content: 5234 字符
  ✓ section.pt-8.border-gray-100: 12456 字符
  ...

💡 建议:
  • 该网站需要JS渲染，确保已安装Playwright
  • 运行: pip install playwright && playwright install chromium
```

---

### 4. `crawl_and_regenerate_with_llm` - 增强版

**新增功能**：支持直接对已有Markdown文件进行大模型重写。

**使用场景**：
- 已经爬取好内容，只需要大模型重写
- 避免重复爬取浪费时间

**参数**：
```python
crawl_and_regenerate_with_llm(
    url=None,                         # URL（与input_file二选一）
    input_file=None,                  # 已有文件（优先使用）
    provider="deepseek",              # 大模型厂商
    model_name=None,                  # 模型名称
    prompt_template=None,             # 自定义提示词
    ...
)
```

**示例1：爬取+重写**
```
爬取 https://example.com 并用 deepseek 重写
```

**示例2：只重写已有文件**
```
用 bailian 的 qwen-plus 重写这个文件：
/path/to/existing_file.md
```

---

## 📊 内容质量评估标准

`crawl_with_quality_check` 工具会根据以下标准评估内容：

| 评估项 | 标准 | 扣分 |
|--------|------|------|
| 内容长度 | < 200字符 | -30分 |
| 标题结构 | 缺少Markdown标题 | -10分 |
| 段落划分 | < 2个段落 | -10分 |
| 特殊字符/乱码 | > 5%特殊字符 | -20分 |
| 重复内容 | 重复率 > 30% | -15分 |
| 链接密度 | 每100字>1链接 | -10分 |

**得分解释**：
- **80-100分 (good)**: 内容质量优秀，无需重写
- **60-79分 (medium)**: 内容可读但可优化，建议重写
- **0-59分 (poor)**: 内容质量差，强烈建议重写

---

## 🎯 典型使用流程

### 流程1：单个网页 - 自动判断是否需要重写

```
1. 用户: "爬取 https://example.com 的内容"
   
2. AI: 使用 crawl_with_quality_check(url="https://example.com")
   
3. 系统输出:
   - 爬取成功
   - 质量评估: 65分 (medium)
   - 建议: 内容质量不佳，建议使用大模型重写
   
4. 用户: "那就用 deepseek 重写吧"
   
5. AI: 使用 crawl_and_regenerate_with_llm(
           input_file="/path/to/crawled_file.md",
           provider="deepseek"
       )
```

### 流程2：批量爬取+AI总结

```
1. 用户: "帮我爬取这几个网页：
         - https://url1.com
         - https://url2.com
         - https://url3.com
         然后用百炼的 qwen-plus 生成总结报告"
   
2. AI: 使用 crawl_and_summarize(
           urls=["url1", "url2", "url3"],
           output_dir="/path/to/output",
           llm_provider="bailian",
           llm_model="qwen-plus"
       )
   
3. 系统输出:
   - 爬取3个URL: 成功2个，失败1个
   - 生成总结报告: /path/to/总结报告_xxx.md
   - 保存原始文件: 2个 .md 文件
```

### 流程3：爬取失败 - 快速诊断

```
1. 用户: "爬取 https://example.com"
   
2. AI: 使用 crawl_single_url(url="https://example.com")
   
3. 系统输出: ❌ 爬取失败: 无法获取网页内容
   
4. AI: 使用 diagnose_crawl_failure(url="https://example.com")
   
5. 系统输出:
   - 检测到SPA特征，需要JS渲染
   - 建议: 安装 Playwright
   
6. 用户: "我已经安装了 Playwright，再试一次"
   
7. AI: 使用 crawl_single_url(url="https://example.com", verbose=True)
```

---

## 🔧 配置要求

### 1. Playwright（JS渲染）

如果网站需要JS渲染（如 hf-mirror.com），需要安装：

```bash
pip install playwright
playwright install chromium
```

### 2. 大模型API密钥

在 `.env` 文件中配置API密钥：

```env
# 硅基流动
SILICONFLOW_API_KEY=your_key_here

# DeepSeek
DEEPSEEK_API_KEY=your_key_here

# 百炼（阿里云）
BAILIAN_API_KEY=your_key_here

# Kimi（月之暗面）
KIMI_API_KEY=your_key_here
```

---

## 📝 最佳实践

### 1. 优先使用质量检查

对于不确定质量的网页，使用 `crawl_with_quality_check` 而不是 `crawl_single_url`：

```python
# ❌ 不推荐
crawl_single_url(url)  # 不知道内容质量

# ✅ 推荐
crawl_with_quality_check(url)  # 自动评估质量
```

### 2. 批量处理用专用工具

需要AI理解和总结多个网页时，使用 `crawl_and_summarize`：

```python
# ❌ 不推荐
# 分别爬取3个URL，然后手动合并
crawl_single_url(url1)
crawl_single_url(url2)
crawl_single_url(url3)
# ... 手动调用大模型

# ✅ 推荐
crawl_and_summarize(
    urls=[url1, url2, url3],
    llm_provider="bailian",
    llm_model="qwen-plus"
)
```

### 3. 爬取失败立即诊断

遇到爬取失败时，立即使用诊断工具：

```python
# ❌ 不推荐
# 反复重试相同参数
crawl_single_url(url, max_retries=10)  # 浪费时间

# ✅ 推荐
# 先诊断原因
diagnose_crawl_failure(url)  # 快速定位问题
# 然后根据建议调整参数
```

### 4. 避免重复爬取

如果已经有爬取好的文件，直接用大模型处理：

```python
# ❌ 不推荐
crawl_and_regenerate_with_llm(url=url)  # 重新爬取

# ✅ 推荐
crawl_and_regenerate_with_llm(
    input_file="/path/to/existing.md"  # 使用已有文件
)
```

---

## 🐛 常见问题

### Q1: 为什么 hf-mirror.com 爬取很慢？

**A**: hf-mirror.com 需要JS渲染，会启动浏览器，所以比普通爬取慢。通常需要10-15秒。

### Q2: 质量评估说"链接密度过高"是什么意思？

**A**: 可能爬取到了导航菜单或侧边栏。可以尝试：
1. 检查 `crawl_single_url` 的 verbose 日志
2. 使用 `diagnose_crawl_failure` 查看内容选择器
3. 如果确认内容有问题，用大模型重写可以过滤掉无关内容

### Q3: 大模型重写后内容反而变差了？

**A**: 可以自定义提示词：

```python
custom_prompt = """
请帮我整理这份内容，要求：
1. 保留技术细节
2. 不要过度概括
3. 保持原有的代码示例

内容：
{content}
"""

crawl_and_regenerate_with_llm(
    input_file="/path/to/file.md",
    prompt_template=custom_prompt
)
```

### Q4: 如何选择合适的大模型？

**推荐配置**：
- **技术文档**: `deepseek` (准确度高，适合代码和技术内容)
- **通用内容**: `bailian` 的 `qwen-plus` (综合能力强)
- **长文本**: `kimi` (支持超长上下文)
- **低成本**: `siliconflow` (价格便宜)

---

## 📚 相关文档

- [原版工具文档](./README.md)
- [大模型客户端](./llm_client.py)
- [爬虫核心](../crawler.py)

---

## 🎉 总结

增强版MCP工具提供了：

1. ✅ **智能诊断** - 快速定位爬取失败原因
2. ✅ **质量评估** - 自动判断内容是否需要优化
3. ✅ **自动重写** - 一键完成爬取+评估+优化
4. ✅ **批量总结** - AI理解多个网页并生成报告

这些功能让爬取工作更智能、更高效！

