#!/usr/bin/env python3
"""
BasicWebCrawler MCP Server - Smart Version

智能爬取系统，包含：
1. 智能失败检测和自动切换策略
2. 浏览器集成（支持JS渲染的网站）
3. 自动质量评估和LLM优化
4. 一体化的爬取+处理流程
"""

import sys
import os
from pathlib import Path

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入增强版功能
from mcp_server_enhanced import *
import json
import time
from typing import Optional, Dict, Any, List

def detect_js_requirement(url: str) -> Dict[str, Any]:
    """
    快速检测网站是否需要JS渲染
    
    Returns:
        dict: {
            'needs_js': bool,
            'confidence': str ('high', 'medium', 'low'),
            'reasons': list,
            'suggestion': str
        }
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urlparse
    
    reasons = []
    needs_js = False
    confidence = 'low'
    
    try:
        # 快速检查
        response = requests.get(url, timeout=5)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 检查域名
        domain = urlparse(url).netloc
        js_heavy_domains = ['hf-mirror.com', 'huggingface.co', 'github.io', 'vercel.app']
        if any(d in domain for d in js_heavy_domains):
            reasons.append(f"域名 {domain} 通常需要JS渲染")
            needs_js = True
            confidence = 'high'
        
        # 检查HTML特征
        if soup.select_one('#app') or soup.select_one('#root'):
            reasons.append("检测到SPA框架标识（#app或#root）")
            needs_js = True
            confidence = 'high'
        
        if 'react' in html.lower() or 'vue' in html.lower() or 'angular' in html.lower():
            reasons.append("检测到前端框架标识")
            needs_js = True
            confidence = 'medium' if confidence == 'low' else confidence
        
        # 检查内容长度
        if len(soup.get_text(strip=True)) < 500:
            reasons.append("HTML内容过少，可能需要JS加载")
            needs_js = True
            confidence = 'medium' if confidence == 'low' else confidence
        
        # 生成建议
        if needs_js:
            suggestion = "建议使用浏览器工具（browser_extract_content）来爬取此网站"
        else:
            suggestion = "可以使用标准爬虫工具爬取"
            
    except Exception as e:
        reasons.append(f"检测失败: {e}")
        suggestion = "无法确定，建议先尝试标准爬取，失败后使用浏览器工具"
    
    return {
        'needs_js': needs_js,
        'confidence': confidence,
        'reasons': reasons,
        'suggestion': suggestion
    }

@mcp.tool()
def smart_crawl_single_url(
    url: str,
    output_dir: str,
    img_folder: str = "images",
    auto_switch_to_browser: bool = True,
    use_llm_if_low_quality: bool = False,
    llm_provider: str = "deepseek",
    llm_model: Optional[str] = None,
    max_retries: int = 2,
    verbose: bool = False
) -> str:
    """
    智能爬取单个网页 - 自动选择最佳策略
    
    这是一个智能工具，会：
    1. 先检测网站是否需要JS渲染
    2. 选择合适的爬取方式（标准爬虫 vs 浏览器）
    3. 评估内容质量
    4. 可选：使用大模型优化内容
    
    Args:
        url: 要爬取的网页URL
        output_dir: 输出目录（必填）
        img_folder: 图片保存文件夹，默认"images"
        auto_switch_to_browser: 标准爬取失败时，是否自动切换到浏览器模式
        use_llm_if_low_quality: 内容质量低时，是否自动使用大模型优化
        llm_provider: 大模型厂商（siliconflow/deepseek/bailian/kimi）
        llm_model: 大模型名称
        max_retries: 标准爬取的最大重试次数
        verbose: 是否输出详细日志
        
    Returns:
        包含完整处理结果的字符串
    """
    import sys
    
    sys.stderr.write(f"\n{'='*70}\n")
    sys.stderr.write(f"🧠 智能爬取系统启动\n")
    sys.stderr.write(f"{'='*70}\n")
    sys.stderr.write(f"📍 URL: {url}\n")
    sys.stderr.write(f"📁 输出: {output_dir}\n")
    sys.stderr.write(f"{'='*70}\n\n")
    
    result_log = []
    
    # 第一步：快速检测
    sys.stderr.write("🔍 第1步：检测网站特征...\n")
    detection = detect_js_requirement(url)
    
    result_log.append("=" * 70)
    result_log.append("🔍 网站检测结果")
    result_log.append("=" * 70)
    result_log.append(f"需要JS渲染: {'是' if detection['needs_js'] else '否'}")
    result_log.append(f"置信度: {detection['confidence']}")
    result_log.append(f"\n检测依据:")
    for reason in detection['reasons']:
        result_log.append(f"  • {reason}")
    result_log.append(f"\n💡 建议: {detection['suggestion']}")
    result_log.append("")
    
    # 第二步：选择爬取策略
    if detection['needs_js'] and detection['confidence'] == 'high':
        sys.stderr.write("\n✅ 检测到JS渲染网站，直接使用浏览器模式\n")
        result_log.append("📌 选择策略: 浏览器模式（跳过标准爬取）")
        result_log.append("")
        
        # 直接使用浏览器工具
        # 注意：这里需要用户已经在浏览器中打开了页面
        result_log.append("⚠️ 请确保已在浏览器中打开该URL")
        result_log.append("💡 建议：使用 browser_extract_and_save 工具继续处理")
        
        return "\n".join(result_log)
    
    # 第三步：尝试标准爬取
    sys.stderr.write("\n🌐 第2步：尝试标准爬取...\n")
    result_log.append("=" * 70)
    result_log.append("🌐 标准爬取尝试")
    result_log.append("=" * 70)
    
    crawl_result = crawl_single_url(
        url=url,
        img_folder=img_folder,
        output_dir=output_dir,
        max_retries=max_retries,
        verbose=verbose
    )
    
    # 检查是否成功
    if "❌" not in crawl_result and "失败" not in crawl_result:
        sys.stderr.write("✅ 标准爬取成功\n")
        result_log.append("✅ 标准爬取成功")
        result_log.append("")
        result_log.append(crawl_result)
        
        # 第四步：质量检查
        sys.stderr.write("\n📊 第3步：质量评估...\n")
        
        # 提取文件路径
        import re
        file_match = re.search(r'保存文件:\s*(.+\.md)', crawl_result)
        if file_match:
            md_file = file_match.group(1).strip()
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                quality = evaluate_content_quality(content)
                
                result_log.append("")
                result_log.append("=" * 70)
                result_log.append("📊 内容质量评估")
                result_log.append("=" * 70)
                result_log.append(f"质量得分: {quality['score']}/100")
                result_log.append(f"可读性: {quality['readability']}")
                result_log.append(f"建议优化: {'是' if quality['needs_rewrite'] else '否'}")
                
                if quality['issues']:
                    result_log.append(f"\n发现的问题:")
                    for issue in quality['issues']:
                        result_log.append(f"  • {issue}")
                
                # 第五步：决定是否使用LLM
                if use_llm_if_low_quality and quality['needs_rewrite']:
                    sys.stderr.write("\n🤖 第4步：使用大模型优化内容...\n")
                    result_log.append("")
                    result_log.append("🤖 启动大模型优化...")
                    
                    # 调用LLM重写
                    if LLM_AVAILABLE:
                        llm_result = crawl_and_regenerate_with_llm(
                            input_file=md_file,
                            provider=llm_provider,
                            model_name=llm_model,
                            output_dir=output_dir,
                            save_original=True
                        )
                        result_log.append(llm_result)
                    else:
                        result_log.append("⚠️ LLM功能不可用，跳过优化")
                
                elif quality['needs_rewrite']:
                    result_log.append("")
                    result_log.append("💡 建议: 设置 use_llm_if_low_quality=True 自动优化内容")
                
            except Exception as e:
                result_log.append(f"⚠️ 质量评估失败: {e}")
        
        return "\n".join(result_log)
    
    # 标准爬取失败 - 切换到浏览器模式
    sys.stderr.write("\n❌ 标准爬取失败\n")
    result_log.append("❌ 标准爬取失败")
    result_log.append("")
    result_log.append(crawl_result)
    result_log.append("")
    
    if auto_switch_to_browser:
        sys.stderr.write("\n🔄 第3步：切换到浏览器模式...\n")
        result_log.append("=" * 70)
        result_log.append("🔄 自动切换到浏览器模式")
        result_log.append("=" * 70)
        result_log.append("")
        result_log.append("⚠️ 浏览器模式需要手动操作：")
        result_log.append("1. 请在浏览器中打开该URL")
        result_log.append("2. 使用 browser_extract_and_save 工具提取内容")
        result_log.append("")
        result_log.append(f"💡 建议命令：")
        result_log.append(f"   browser_extract_and_save(")
        result_log.append(f"       url='{url}',")
        result_log.append(f"       output_dir='{output_dir}',")
        result_log.append(f"       model_name='GLM模型名称'")
        result_log.append(f"   )")
    else:
        result_log.append("ℹ️ 自动切换已禁用，可设置 auto_switch_to_browser=True 启用")
    
    return "\n".join(result_log)

@mcp.tool()
def browser_extract_and_save(
    current_url: str,
    page_content: str,
    output_dir: str,
    model_name: str,
    img_folder: str = "images",
    use_llm: bool = False,
    llm_provider: str = "deepseek",
    llm_model: Optional[str] = None,
    custom_prompt: Optional[str] = None
) -> str:
    """
    从浏览器提取的内容保存为Markdown文件
    
    这个工具专门用于处理JS渲染的网站：
    1. 接收从浏览器提取的内容（通过browser_evaluate获取）
    2. 保存为Markdown格式
    3. 可选：使用大模型重新整理和优化内容
    
    使用流程：
    1. 先用 browser_navigate 打开网页
    2. 用 browser_evaluate 提取内容：
       () => document.querySelector('main').innerText
    3. 调用本工具保存内容
    
    Args:
        current_url: 当前浏览器的URL
        page_content: 从浏览器提取的页面内容（纯文本或HTML）
        output_dir: 输出目录
        model_name: 模型名称（用于文件命名）
        img_folder: 图片文件夹名称
        use_llm: 是否使用大模型重新整理内容
        llm_provider: 大模型厂商
        llm_model: 大模型名称
        custom_prompt: 自定义提示词
        
    Returns:
        保存结果信息
    """
    import sys
    from pathlib import Path
    from urllib.parse import urlparse
    from datetime import datetime
    
    sys.stderr.write(f"\n{'='*70}\n")
    sys.stderr.write(f"💾 浏览器内容保存工具\n")
    sys.stderr.write(f"{'='*70}\n")
    
    # 创建输出目录
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 创建图片目录
    img_path = output_path / img_folder
    img_path.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{model_name}_{timestamp}.md"
    output_file = output_path / filename
    
    result_log = []
    result_log.append("=" * 70)
    result_log.append("💾 保存浏览器内容")
    result_log.append("=" * 70)
    result_log.append(f"URL: {current_url}")
    result_log.append(f"输出文件: {output_file}")
    result_log.append(f"内容长度: {len(page_content)} 字符")
    result_log.append("")
    
    # 构建Markdown内容
    md_content = f"""# {model_name}

> 来源: {current_url}
> 爬取时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 方式: 浏览器提取

---

{page_content}
"""
    
    # 如果需要使用LLM优化
    if use_llm and LLM_AVAILABLE:
        sys.stderr.write("🤖 使用大模型优化内容...\n")
        result_log.append("🤖 使用大模型优化内容...")
        
        try:
            # 加载环境变量
            from llm_client import LLMClientFactory
            LLMClientFactory.load_env_config()
            
            # 创建客户端（设置更长的超时时间，用于处理长内容）
            llm_client = LLMClientFactory.create_client(
                provider=llm_provider,
                model_name=llm_model,
                timeout=300  # 5分钟超时，足够处理长内容
            )
            
            # 构建提示词
            if custom_prompt is None:
                prompt = f"""你是一个专业的技术文档整理助手。我从网页中提取了以下内容，请帮我：

1. 整理成结构化的Markdown文档
2. 提取关键信息，去除冗余内容
3. 使用清晰的标题层级
4. 保留重要的技术细节
5. 如果有代码示例，保持代码格式

网页URL: {current_url}
标题: {model_name}

原始内容：
{page_content}

请输出整理后的Markdown文档："""
            else:
                prompt = custom_prompt.replace("{content}", page_content)
                prompt = prompt.replace("{url}", current_url)
                prompt = prompt.replace("{title}", model_name)
            
            # 调用大模型
            messages = [{"role": "user", "content": prompt}]
            start_time = time.time()
            llm_result = llm_client.chat_completion(messages)
            end_time = time.time()
            
            if llm_result.get("error"):
                result_log.append(f"⚠️ 大模型调用失败: {llm_result['error']}")
                result_log.append("📝 保存原始内容...")
            else:
                optimized_content = llm_result.get("content", "")
                
                # 构建优化后的内容
                md_content = f"""# {model_name}

> 来源: {current_url}
> 爬取时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 方式: 浏览器提取 + 大模型优化
> 大模型: {llm_result.get('provider')} - {llm_result.get('model')}
> 处理时间: {end_time - start_time:.2f} 秒

---

{optimized_content}
"""
                
                result_log.append(f"✅ 大模型优化完成")
                result_log.append(f"   模型: {llm_result.get('provider')} - {llm_result.get('model')}")
                result_log.append(f"   耗时: {end_time - start_time:.2f} 秒")
                result_log.append(f"   Token: {llm_result.get('usage', {}).get('total_tokens', 'N/A')}")
                
        except Exception as e:
            result_log.append(f"⚠️ LLM处理失败: {e}")
            result_log.append("📝 保存原始内容...")
    
    # 保存文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        result_log.append("")
        result_log.append("✅ 文件保存成功")
        result_log.append(f"📄 文件路径: {output_file}")
        result_log.append(f"📊 文件大小: {output_file.stat().st_size} 字节")
        
        # 质量评估
        quality = evaluate_content_quality(md_content)
        result_log.append("")
        result_log.append("=" * 70)
        result_log.append("📊 内容质量评估")
        result_log.append("=" * 70)
        result_log.append(f"质量得分: {quality['score']}/100")
        result_log.append(f"可读性: {quality['readability']}")
        
        if quality['issues']:
            result_log.append(f"\n发现的问题:")
            for issue in quality['issues']:
                result_log.append(f"  • {issue}")
        
        if quality['needs_rewrite'] and not use_llm:
            result_log.append("")
            result_log.append("💡 建议: 设置 use_llm=True 使用大模型优化内容")
        
    except Exception as e:
        result_log.append(f"❌ 保存失败: {e}")
    
    return "\n".join(result_log)

@mcp.tool()
def batch_browser_extract(
    urls: List[str],
    output_dir: str,
    wait_for_user: bool = True,
    use_llm_summary: bool = True,
    llm_provider: str = "bailian",
    llm_model: Optional[str] = None
) -> str:
    """
    批量处理多个需要浏览器的URL
    
    这个工具用于批量处理JS渲染网站：
    1. 提供URL列表
    2. 系统会逐个提示用户在浏览器中打开
    3. 提取内容并保存
    4. 可选：最后生成AI总结报告
    
    Args:
        urls: URL列表
        output_dir: 输出目录
        wait_for_user: 是否等待用户确认（默认True）
        use_llm_summary: 是否生成AI总结报告
        llm_provider: 大模型厂商
        llm_model: 大模型名称
        
    Returns:
        批量处理指引信息
    """
    import sys
    from pathlib import Path
    from urllib.parse import urlparse
    
    sys.stderr.write(f"\n{'='*70}\n")
    sys.stderr.write(f"📋 批量浏览器提取任务\n")
    sys.stderr.write(f"{'='*70}\n")
    sys.stderr.write(f"URL数量: {len(urls)}\n")
    sys.stderr.write(f"{'='*70}\n\n")
    
    result = []
    result.append("=" * 70)
    result.append("📋 批量浏览器提取指引")
    result.append("=" * 70)
    result.append(f"待处理URL: {len(urls)}")
    result.append(f"输出目录: {output_dir}")
    result.append("")
    
    # 为每个URL生成处理步骤
    for i, url in enumerate(urls, 1):
        domain = urlparse(url).netloc
        model_name = url.split('/')[-1] if '/' in url else domain
        
        result.append(f"\n{'─'*70}")
        result.append(f"任务 {i}/{len(urls)}: {model_name}")
        result.append(f"{'─'*70}")
        result.append(f"URL: {url}")
        result.append("")
        result.append("执行步骤：")
        result.append("")
        result.append(f"1️⃣ 在浏览器中打开URL:")
        result.append(f"   browser_navigate(url='{url}')")
        result.append("")
        result.append(f"2️⃣ 等待页面加载完成（观察页面）")
        result.append("")
        result.append(f"3️⃣ 提取页面主要内容:")
        result.append(f"   browser_evaluate(")
        result.append(f"       function='() => document.querySelector(\"main\").innerText'")
        result.append(f"   )")
        result.append("")
        result.append(f"4️⃣ 保存提取的内容:")
        result.append(f"   browser_extract_and_save(")
        result.append(f"       current_url='{url}',")
        result.append(f"       page_content='<提取的内容>',")
        result.append(f"       output_dir='{output_dir}',")
        result.append(f"       model_name='{model_name}',")
        result.append(f"       use_llm=True")
        result.append(f"   )")
        result.append("")
    
    # 如果需要总结
    if use_llm_summary:
        result.append(f"\n{'='*70}")
        result.append("🤖 最后一步：生成AI总结报告")
        result.append("="* 70)
        result.append("")
        result.append("所有文件处理完成后，使用以下工具生成总结：")
        result.append("")
        result.append(f"crawl_and_summarize(")
        result.append(f"    urls={urls},")
        result.append(f"    output_dir='{output_dir}',")
        result.append(f"    llm_provider='{llm_provider}',")
        model_str = f"'{llm_model}'" if llm_model else "None"
        result.append(f"    llm_model={model_str},")
        result.append(f"    save_originals=False  # 已经保存过了")
        result.append(f")")
    
    result.append("")
    result.append("=" * 70)
    result.append("💡 提示")
    result.append("=" * 70)
    result.append("• 请按顺序执行每个URL的处理步骤")
    result.append("• 确保每个页面完全加载后再提取内容")
    result.append("• 可以调整 document.querySelector 的选择器来匹配页面结构")
    result.append("• 设置 use_llm=True 可以让AI优化提取的内容")
    
    return "\n".join(result)

if __name__ == "__main__":
    mcp.run()

