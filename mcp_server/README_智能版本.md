# BasicWebCrawler MCP 智能版本使用指南

## 🎯 核心改进

智能版本解决了原版的主要痛点：

### ❌ 原版问题
```
爬取失败(需要JS) → 重试2次 → 再次失败 → 手动尝试 → 繁琐低效
```

### ✅ 智能版本
```
爬取失败(需要JS) → 自动检测原因 → 提示最佳方案 → 一键执行
```

## 🚀 新增工具

### 1. `smart_crawl_single_url` - 智能爬取

**核心特性**：
- ✅ 自动检测网站是否需要JS渲染
- ✅ 智能选择最佳爬取策略
- ✅ 失败后自动给出解决方案
- ✅ 内置质量评估和LLM优化

**使用场景**：
```
用户："爬取 https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base"

智能系统：
1. 检测：这是JS渲染网站（置信度：高）
2. 决策：跳过标准爬取，建议使用浏览器
3. 提示：具体操作步骤
```

**参数**：
```python
smart_crawl_single_url(
    url="https://example.com",
    output_dir="/path/to/output",        # 必填
    img_folder="images",                 # 图片目录
    auto_switch_to_browser=True,         # 失败时自动建议浏览器方案
    use_llm_if_low_quality=False,        # 低质量内容自动优化
    llm_provider="deepseek",             # 大模型厂商
    llm_model=None,                      # 模型名称
    max_retries=2,                       # 标准爬取重试次数
    verbose=False                        # 详细日志
)
```

**示例**：
```
爬取 https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base
保存到 /Users/damon/Desktop/中移互联网-品质部AI智能客服
如果质量不佳就用deepseek优化
```

---

### 2. `browser_extract_and_save` - 浏览器内容保存

**核心特性**：
- ✅ 直接从浏览器提取的内容保存为Markdown
- ✅ 支持大模型实时优化
- ✅ 自动质量评估
- ✅ 智能文件命名

**使用流程**：
```python
# 第1步：打开页面
browser_navigate(url="https://hf-mirror.com/...")

# 第2步：提取内容
content = browser_evaluate(
    function="() => document.querySelector('main').innerText"
)

# 第3步：保存并优化
browser_extract_and_save(
    current_url="https://hf-mirror.com/...",
    page_content=content,
    output_dir="/path/to/output",
    model_name="GLM-4.1V-9B-Base",
    use_llm=True,                # 使用大模型优化
    llm_provider="deepseek"
)
```

**参数**：
```python
browser_extract_and_save(
    current_url: str,              # 当前浏览器URL
    page_content: str,             # 提取的内容
    output_dir: str,               # 输出目录
    model_name: str,               # 模型名称（用于文件命名）
    img_folder="images",           # 图片目录
    use_llm=False,                 # 是否用LLM优化
    llm_provider="deepseek",       # 大模型厂商
    llm_model=None,                # 模型名称
    custom_prompt=None             # 自定义提示词
)
```

---

### 3. `batch_browser_extract` - 批量浏览器处理

**核心特性**：
- ✅ 批量处理多个JS渲染网站
- ✅ 为每个URL生成详细操作步骤
- ✅ 支持最终AI总结
- ✅ 完整的任务指引

**使用场景**：
```
用户："爬取这3个HuggingFace模型页面并总结"

系统输出：
• 任务1/3: GLM-4.1V-9B-Base
  - 步骤1: browser_navigate(...)
  - 步骤2: 等待加载
  - 步骤3: browser_evaluate(...)
  - 步骤4: browser_extract_and_save(...)
• 任务2/3: ...
• 任务3/3: ...
• 最后: crawl_and_summarize(...)
```

**参数**：
```python
batch_browser_extract(
    urls=["url1", "url2", "url3"],  # URL列表
    output_dir="/path/to/output",   # 输出目录
    wait_for_user=True,             # 等待用户确认
    use_llm_summary=True,           # 生成AI总结
    llm_provider="bailian",         # 大模型厂商
    llm_model="qwen-plus"           # 模型名称
)
```

---

## 📖 完整使用流程

### 场景：爬取3个HuggingFace模型页面

#### 方案A：智能自动化（推荐）

```python
# 第1步：批量任务规划
batch_browser_extract(
    urls=[
        "https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
        "https://hf-mirror.com/zai-org/GLM-4.1V-9B-Thinking",
        "https://hf-mirror.com/zai-org/GLM-4.5V"
    ],
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服",
    use_llm_summary=True,
    llm_provider="bailian",
    llm_model="qwen-plus"
)

# 系统会输出详细的操作步骤，然后按提示执行即可
```

#### 方案B：逐个手动处理

**处理第1个URL**：
```python
# 1. 智能爬取（会自动检测并建议）
smart_crawl_single_url(
    url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服",
    auto_switch_to_browser=True
)

# 系统输出：
# "检测到JS渲染网站，建议使用浏览器模式"

# 2. 在浏览器中打开
browser_navigate(url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base")

# 3. 提取内容
content = browser_evaluate(
    function="() => document.querySelector('main').innerText"
)

# 4. 保存并优化
browser_extract_and_save(
    current_url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
    page_content=content,
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服",
    model_name="GLM-4.1V-9B-Base",
    use_llm=True,
    llm_provider="deepseek"
)
```

**重复处理第2、3个URL**...

**最后生成总结**：
```python
crawl_and_summarize(
    urls=[...],  # 已处理的URL列表
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服",
    llm_provider="bailian",
    llm_model="qwen-plus",
    save_originals=False  # 已经保存过了
)
```

---

## 🔄 智能决策树

```
用户请求爬取URL
    ↓
[smart_crawl_single_url]
    ↓
检测网站特征
    ↓
    ├─ 需要JS? (高置信度)
    │   ↓
    │   跳过标准爬取
    │   ↓
    │   提示：使用浏览器工具
    │   ↓
    │   [batch_browser_extract] 规划任务
    │
    └─ 不需要JS 或 置信度低
        ↓
        尝试标准爬取
        ↓
        ├─ 成功
        │   ↓
        │   质量评估
        │   ↓
        │   ├─ 质量好 → 完成
        │   └─ 质量差 → 建议LLM优化
        │
        └─ 失败
            ↓
            auto_switch_to_browser?
            ↓
            ├─ 是 → 提示浏览器方案
            └─ 否 → 返回失败信息
```

---

## 💡 最佳实践

### 1. 首次爬取未知网站
```python
# 使用智能爬取，让系统自动判断
smart_crawl_single_url(
    url="https://unknown-site.com",
    output_dir="/path/to/output",
    auto_switch_to_browser=True,     # 失败时自动建议方案
    use_llm_if_low_quality=True      # 自动优化内容
)
```

### 2. 已知是JS渲染网站
```python
# 直接使用批量浏览器处理
batch_browser_extract(
    urls=[...],
    output_dir="/path/to/output",
    use_llm_summary=True
)
```

### 3. 需要高质量内容
```python
# 开启LLM优化
browser_extract_and_save(
    ...,
    use_llm=True,
    llm_provider="deepseek",  # 技术文档推荐deepseek
    custom_prompt="""
请整理这份技术文档，要求：
1. 保留所有技术细节
2. 优化结构层次
3. 添加必要的说明
4. 保持代码格式
    """
)
```

### 4. 批量处理+总结
```python
# 一站式解决方案
batch_browser_extract(
    urls=[...],
    output_dir="/path/to/output",
    use_llm_summary=True,
    llm_provider="bailian",
    llm_model="qwen-plus"
)
# 按提示逐个处理后，最后会自动生成总结报告
```

---

## ⚙️ 配置要求

### 1. 浏览器扩展
确保已安装 Cursor Browser Extension（Cursor内置）

### 2. 大模型API密钥
在 `.env` 文件中配置：
```env
# DeepSeek（推荐用于技术文档）
DEEPSEEK_API_KEY=your_key_here

# 百炼/阿里云（推荐用于通用内容）
BAILIAN_API_KEY=your_key_here

# Kimi（支持超长文本）
KIMI_API_KEY=your_key_here

# 硅基流动（低成本）
SILICONFLOW_API_KEY=your_key_here
```

### 3. Python依赖
```bash
pip install -r requirements.txt
```

---

## 🆚 版本对比

| 特性 | 原版 | 增强版 | 智能版 |
|------|------|--------|--------|
| 标准爬取 | ✅ | ✅ | ✅ |
| 质量评估 | ❌ | ✅ | ✅ |
| 失败诊断 | ❌ | ✅ | ✅ |
| LLM优化 | ✅ | ✅ | ✅ |
| **智能检测** | ❌ | ❌ | ✅ |
| **自动切换策略** | ❌ | ❌ | ✅ |
| **浏览器集成** | ❌ | ❌ | ✅ |
| **批量任务规划** | ❌ | ❌ | ✅ |

---

## 🎉 总结

智能版本的核心优势：

1. **更智能** - 自动检测网站特征，选择最佳策略
2. **更快速** - 避免无效重试，直接使用正确方法
3. **更简单** - 一个工具搞定，无需手动判断
4. **更完整** - 浏览器+爬虫+LLM完整集成

**推荐使用场景**：
- ✅ 爬取JS渲染的现代网站（如HuggingFace、GitHub Pages）
- ✅ 需要高质量内容输出
- ✅ 批量处理多个网站
- ✅ 不确定网站类型，需要智能判断

**不推荐使用场景**：
- ❌ 简单的静态网页（用标准爬取即可）
- ❌ 已有成熟配置的网站（直接用crawl_single_url）

