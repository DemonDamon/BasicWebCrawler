# 示例：爬取HuggingFace模型页面（智能版）

## 任务描述

爬取以下3个HuggingFace模型页面到本地：

1. https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base → 保存到 `GLM-4.1V-9B-Base/`
2. https://hf-mirror.com/zai-org/GLM-4.1V-9B-Thinking → 保存到 `GLM-4.1V-9B-Thinking/`
3. https://hf-mirror.com/zai-org/GLM-4.5V → 保存到 `GLM-4.5V/`

输出目录：`/Users/damon/Desktop/中移互联网-品质部AI智能客服`

---

## 🚫 原版方式（不推荐）

```python
# 第1步：尝试标准爬取
crawl_single_url(
    url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服"
)

# 结果：❌ 爬取失败：该网站需要JS渲染，已自动使用Playwright
# 问题：重试2次浪费时间，没有给出解决方案
```

---

## ✅ 智能版方式（推荐）

### 方法一：自动化批量处理（最简单）

```python
# 一条命令搞定规划
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
```

**系统会输出**：
```
============================================================
📋 批量浏览器提取指引
============================================================
待处理URL: 3
输出目录: /Users/damon/Desktop/中移互联网-品质部AI智能客服

──────────────────────────────────────────────────────────
任务 1/3: GLM-4.1V-9B-Base
──────────────────────────────────────────────────────────
URL: https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base

执行步骤：

1️⃣ 在浏览器中打开URL:
   browser_navigate(url='https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base')

2️⃣ 等待页面加载完成（观察页面）

3️⃣ 提取页面主要内容:
   browser_evaluate(
       function='() => document.querySelector("main").innerText'
   )

4️⃣ 保存提取的内容:
   browser_extract_and_save(
       current_url='https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base',
       page_content='<提取的内容>',
       output_dir='/Users/damon/Desktop/中移互联网-品质部AI智能客服',
       model_name='GLM-4.1V-9B-Base',
       use_llm=True
   )

[... 任务2、3的步骤 ...]

============================================================
🤖 最后一步：生成AI总结报告
============================================================

所有文件处理完成后，使用以下工具生成总结：

crawl_and_summarize(
    urls=[...],
    output_dir='/Users/damon/Desktop/中移互联网-品质部AI智能客服',
    llm_provider='bailian',
    llm_model='qwen-plus',
    save_originals=False
)
```

**然后按步骤执行即可！**

---

### 方法二：逐个处理（适合需要精细控制）

#### 处理第1个页面：GLM-4.1V-9B-Base

**步骤1：打开页面**
```python
browser_navigate(url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base")
```

**步骤2：等待加载**
观察浏览器窗口，确保页面完全加载。

**步骤3：提取主要内容**
```python
browser_evaluate(
    function="() => document.querySelector('main').innerText"
)
```

系统返回内容类似：
```
"zai-org\n/\nGLM-4.1V-9B-Base\n...[大量文本]..."
```

**步骤4：保存并优化**
```python
browser_extract_and_save(
    current_url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
    page_content="<步骤3提取的内容>",
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服/GLM-4.1V-9B-Base",
    model_name="GLM-4.1V-9B-Base",
    use_llm=True,
    llm_provider="deepseek"
)
```

**输出结果**：
```
============================================================
💾 保存浏览器内容
============================================================
URL: https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base
输出文件: .../GLM-4.1V-9B-Base/GLM-4.1V-9B-Base_20251208_150000.md
内容长度: 15234 字符

🤖 使用大模型优化内容...
✅ 大模型优化完成
   模型: deepseek - deepseek-chat
   耗时: 8.5 秒
   Token: 3456

✅ 文件保存成功
📄 文件路径: .../GLM-4.1V-9B-Base_20251208_150000.md
📊 文件大小: 18234 字节

============================================================
📊 内容质量评估
============================================================
质量得分: 92/100
可读性: good
```

#### 处理第2个页面：GLM-4.1V-9B-Thinking

重复上述4个步骤，只需修改URL和model_name：

```python
# 1. 打开
browser_navigate(url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Thinking")

# 2. 等待加载

# 3. 提取
browser_evaluate(function="() => document.querySelector('main').innerText")

# 4. 保存
browser_extract_and_save(
    current_url="https://hf-mirror.com/zai-org/GLM-4.1V-9B-Thinking",
    page_content="<提取的内容>",
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服/GLM-4.1V-9B-Thinking",
    model_name="GLM-4.1V-9B-Thinking",
    use_llm=True,
    llm_provider="deepseek"
)
```

#### 处理第3个页面：GLM-4.5V

```python
# 1. 打开
browser_navigate(url="https://hf-mirror.com/zai-org/GLM-4.5V")

# 2. 等待加载

# 3. 提取
browser_evaluate(function="() => document.querySelector('main').innerText")

# 4. 保存
browser_extract_and_save(
    current_url="https://hf-mirror.com/zai-org/GLM-4.5V",
    page_content="<提取的内容>",
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服/GLM-4.5V",
    model_name="GLM-4.5V",
    use_llm=True,
    llm_provider="deepseek"
)
```

#### 最后：生成总结报告

```python
crawl_and_summarize(
    urls=[
        "https://hf-mirror.com/zai-org/GLM-4.1V-9B-Base",
        "https://hf-mirror.com/zai-org/GLM-4.1V-9B-Thinking",
        "https://hf-mirror.com/zai-org/GLM-4.5V"
    ],
    output_dir="/Users/damon/Desktop/中移互联网-品质部AI智能客服",
    llm_provider="bailian",
    llm_model="qwen-plus",
    summary_prompt="""
请为这3个GLM视觉语言模型生成对比分析报告，包括：
1. 每个模型的核心特点和参数
2. 性能对比（如果有benchmark数据）
3. 使用场景和适用性
4. 技术亮点总结
    """,
    save_originals=False  # 已经保存过了
)
```

**最终输出**：
```
✅ 批量爬取+总结完成！

============================================================
📊 处理统计
============================================================
• 总URL数: 3
• 成功爬取: 3
• 失败: 0
• 大模型: bailian - qwen-plus
• 生成耗时: 12.3 秒
• Token使用: 5678

============================================================
📁 文件信息
============================================================
• 总结报告: .../总结报告_20251208_150500.md
• 原始文件: 未保存
• 输出目录: /Users/damon/Desktop/中移互联网-品质部AI智能客服

============================================================
📝 总结预览
============================================================
# GLM视觉语言模型系列对比分析

## 1. GLM-4.1V-9B-Base
GLM-4.1V-9B-Base是基础版本...

## 2. GLM-4.1V-9B-Thinking
GLM-4.1V-9B-Thinking是推理增强版本...

## 3. GLM-4.5V
GLM-4.5V是系列最新版本...
...
```

---

## 📂 最终文件结构

```
中移互联网-品质部AI智能客服/
├── GLM-4.1V-9B-Base/
│   ├── images/
│   │   ├── rl.jpeg
│   │   ├── bench.jpeg
│   │   └── ...
│   └── GLM-4.1V-9B-Base_20251208_150000.md
├── GLM-4.1V-9B-Thinking/
│   ├── images/
│   │   └── ...
│   └── GLM-4.1V-9B-Thinking_20251208_150200.md
├── GLM-4.5V/
│   ├── images/
│   │   └── ...
│   └── GLM-4.5V_20251208_150400.md
└── 总结报告_20251208_150500.md
```

---

## 🎯 核心改进对比

| 步骤 | 原版 | 智能版 |
|------|------|--------|
| 检测网站 | ❌ 直接尝试 | ✅ 先检测特征 |
| 失败处理 | ❌ 重试2次后放弃 | ✅ 立即给出方案 |
| 人工介入 | ❌ 需要手动判断 | ✅ 自动规划步骤 |
| 内容优化 | ❌ 需要额外调用 | ✅ 一体化处理 |
| 批量处理 | ❌ 逐个手动 | ✅ 自动规划 |

---

## 💡 关键提示

1. **提取内容选择器可调整**
   ```javascript
   // 默认
   () => document.querySelector('main').innerText
   
   // 如果main不存在，可以尝试
   () => document.body.innerText
   
   // 或者特定选择器
   () => document.querySelector('.model-card-content').innerText
   ```

2. **LLM提供商选择**
   - `deepseek`: 适合技术文档，准确度高
   - `bailian` + `qwen-plus`: 综合能力强，适合总结
   - `kimi`: 支持超长文本

3. **自定义提示词**
   ```python
   browser_extract_and_save(
       ...,
       custom_prompt="""
   请整理这份模型介绍文档，要求：
   1. 保留benchmark数据表格
   2. 突出模型特点
   3. 用中文重写（如果是英文）
   4. 添加使用建议
   
   原始内容：
   {content}
       """
   )
   ```

---

## 🎉 总结

智能版本让爬取JS渲染网站从：
- **繁琐** → **简单**
- **盲目尝试** → **智能决策**
- **手动拼凑** → **自动化流程**

推荐使用 **方法一（批量自动化）** 来处理这类任务！

