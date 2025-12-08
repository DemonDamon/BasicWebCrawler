#!/usr/bin/env python3
"""
BasicWebCrawler MCP Server - Enhanced Version

增强功能：
1. 更详细的爬取失败诊断
2. 内容质量自动评估
3. 智能决策是否需要大模型重写
4. 明确的"爬取+总结"工具
"""

import sys
import os
from pathlib import Path

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server import *
import re
from typing import Optional, Dict, Any

def evaluate_content_quality(content: str) -> Dict[str, Any]:
    """
    评估内容质量
    
    Returns:
        dict: {
            'score': float (0-100),
            'length': int,
            'readability': str ('good', 'medium', 'poor'),
            'needs_rewrite': bool,
            'issues': list
        }
    """
    if not content:
        return {
            'score': 0,
            'length': 0,
            'readability': 'poor',
            'needs_rewrite': True,
            'issues': ['内容为空']
        }
    
    issues = []
    score = 100
    
    # 1. 长度检查
    length = len(content)
    if length < 200:
        issues.append('内容过短（<200字符）')
        score -= 30
    
    # 2. 结构检查
    has_headers = bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE))
    if not has_headers:
        issues.append('缺少标题结构')
        score -= 10
    
    # 3. 段落检查
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    if len(paragraphs) < 2:
        issues.append('段落划分不清晰')
        score -= 10
    
    # 4. 特殊字符/乱码检查
    weird_chars = re.findall(r'[^\w\s\-_.,;:!?，。；：！？（）【】《》""''\n#*`]', content)
    if len(weird_chars) > length * 0.05:  # 超过5%的特殊字符
        issues.append(f'包含大量特殊字符/乱码 ({len(weird_chars)}个)')
        score -= 20
    
    # 5. 重复内容检查
    lines = content.split('\n')
    unique_lines = set(line.strip() for line in lines if line.strip())
    if len(lines) > 10 and len(unique_lines) / len(lines) < 0.7:
        issues.append('存在大量重复内容')
        score -= 15
    
    # 6. 链接密度检查（过多链接可能是导航菜单）
    link_count = len(re.findall(r'\[.*?\]\(.*?\)', content))
    if link_count > length / 100:  # 每100字符超过1个链接
        issues.append('链接密度过高（可能是菜单内容）')
        score -= 10
    
    score = max(0, score)
    
    # 判断可读性
    if score >= 80:
        readability = 'good'
        needs_rewrite = False
    elif score >= 60:
        readability = 'medium'
        needs_rewrite = True
    else:
        readability = 'poor'
        needs_rewrite = True
    
    return {
        'score': score,
        'length': length,
        'readability': readability,
        'needs_rewrite': needs_rewrite,
        'issues': issues
    }

@mcp.tool()
def crawl_with_quality_check(
    url: str,
    img_folder: str = "images",
    use_cookies: bool = False,
    cookies_file: Optional[str] = None,
    output_dir: Optional[str] = None,
    max_retries: int = 2,
    auto_rewrite: bool = False,
    llm_provider: str = "deepseek",
    llm_model: Optional[str] = None,
    verbose: bool = False
) -> str:
    """
    爬取单个网页并进行质量检查，可选自动用大模型重写
    
    Args:
        url: 要爬取的网页URL
        img_folder: 图片保存文件夹路径
        use_cookies: 是否使用cookies
        cookies_file: cookies文件路径
        output_dir: 输出目录
        max_retries: 最大重试次数
        auto_rewrite: 当内容质量不佳时，是否自动用大模型重写
        llm_provider: 大模型厂商（siliconflow/deepseek/bailian/kimi）
        llm_model: 大模型名称（可选）
        verbose: 是否输出详细日志
        
    Returns:
        包含爬取结果和质量评估的字符串
    """
    import sys
    import time
    from pathlib import Path
    
    # 第一步：爬取内容
    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"📡 开始爬取: {url}\n")
    sys.stderr.write(f"{'='*60}\n")
    
    # 使用原有的爬取函数
    result = crawl_single_url(
        url=url,
        img_folder=img_folder,
        use_cookies=use_cookies,
        cookies_file=cookies_file,
        output_dir=output_dir,
        max_retries=max_retries,
        verbose=verbose
    )
    
    # 检查爬取是否成功
    if "❌" in result or "失败" in result:
        return result  # 直接返回失败信息
    
    # 第二步：提取生成的文件路径
    import re
    file_match = re.search(r'保存文件:\s*(.+\.md)', result)
    if not file_match:
        return result + "\n\n⚠️ 无法找到生成的文件路径，跳过质量检查"
    
    md_file_path = file_match.group(1).strip()
    
    try:
        # 读取生成的Markdown内容
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return result + f"\n\n⚠️ 读取文件失败: {e}"
    
    # 第三步：质量评估
    sys.stderr.write(f"\n📊 评估内容质量...\n")
    quality = evaluate_content_quality(content)
    
    quality_report = f"""
{'='*60}
📊 内容质量评估
{'='*60}
• 质量得分: {quality['score']}/100
• 内容长度: {quality['length']} 字符
• 可读性: {quality['readability']}
• 建议重写: {'是' if quality['needs_rewrite'] else '否'}
"""
    
    if quality['issues']:
        quality_report += f"\n发现的问题:\n"
        for issue in quality['issues']:
            quality_report += f"  • {issue}\n"
    
    sys.stderr.write(quality_report)
    
    # 第四步：决定是否需要大模型重写
    final_result = result + quality_report
    
    if auto_rewrite and quality['needs_rewrite']:
        sys.stderr.write(f"\n🤖 内容质量不佳，启动大模型重写...\n")
        
        # 调用大模型重写
        rewrite_result = crawl_and_regenerate_with_llm(
            url=url,
            provider=llm_provider,
            model_name=llm_model,
            img_folder=img_folder,
            output_dir=output_dir,
            use_cookies=use_cookies,
            cookies_file=cookies_file,
            max_retries=0,  # 不重新爬取，直接使用已有内容
            save_original=True
        )
        
        final_result += f"\n\n{'='*60}\n🤖 大模型重写结果\n{'='*60}\n{rewrite_result}"
    
    elif quality['needs_rewrite'] and not auto_rewrite:
        final_result += f"\n\n💡 提示: 内容质量不佳，建议使用大模型重写\n"
        final_result += f"   可以设置 auto_rewrite=True 自动重写\n"
        final_result += f"   或使用 crawl_and_regenerate_with_llm 工具手动重写"
    
    return final_result

@mcp.tool()
def crawl_and_summarize(
    urls: list,
    output_dir: str,
    llm_provider: str = "bailian",
    llm_model: Optional[str] = None,
    summary_prompt: Optional[str] = None,
    img_folder: str = "images",
    use_cookies: bool = False,
    cookies_file: Optional[str] = None,
    save_originals: bool = True
) -> str:
    """
    爬取多个URL并用大模型生成总结报告
    
    这个工具专门用于处理"爬取xx、xx、xx网页，然后用bailian的qwen-plus总结"这类需求
    
    Args:
        urls: 要爬取的URL列表
        output_dir: 输出目录
        llm_provider: 大模型厂商（siliconflow/deepseek/bailian/kimi）
        llm_model: 大模型名称（如 qwen-plus）
        summary_prompt: 自定义总结提示词
        img_folder: 图片保存文件夹
        use_cookies: 是否使用cookies
        cookies_file: cookies文件路径
        save_originals: 是否保存原始爬取内容
        
    Returns:
        包含爬取和总结结果的字符串
    """
    if not LLM_AVAILABLE:
        return "❌ 错误: llm_client 模块不可用"
    
    import sys
    import time
    from pathlib import Path
    
    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"🎯 批量爬取+总结任务\n")
    sys.stderr.write(f"{'='*60}\n")
    sys.stderr.write(f"• URL数量: {len(urls)}\n")
    sys.stderr.write(f"• 大模型: {llm_provider} - {llm_model or '默认模型'}\n")
    sys.stderr.write(f"{'='*60}\n\n")
    
    # 创建输出目录
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 第一步：爬取所有URL
    crawled_contents = []
    failed_urls = []
    
    for i, url in enumerate(urls, 1):
        sys.stderr.write(f"\n[{i}/{len(urls)}] 爬取: {url}\n")
        
        # 使用原有爬取函数
        try:
            md_content, title = fetch_and_convert_to_markdown(
                url=url,
                img_folder=str(target_dir / img_folder),
                cookies=None,  # TODO: 支持cookies
                verbose=False
            )
            
            if md_content and len(md_content) > 200:
                crawled_contents.append({
                    'url': url,
                    'title': title,
                    'content': md_content
                })
                sys.stderr.write(f"  ✓ 成功\n")
                
                # 保存原始内容
                if save_originals:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    original_file = target_dir / f"{sanitize_filename(title)}_{timestamp}.md"
                    with open(original_file, 'w', encoding='utf-8') as f:
                        f.write(md_content)
            else:
                failed_urls.append(url)
                sys.stderr.write(f"  ✗ 失败（内容为空）\n")
                
        except Exception as e:
            failed_urls.append(url)
            sys.stderr.write(f"  ✗ 失败: {e}\n")
    
    if not crawled_contents:
        return f"❌ 所有URL爬取失败\n失败的URL:\n" + "\n".join([f"• {url}" for url in failed_urls])
    
    # 第二步：合并内容
    sys.stderr.write(f"\n📝 合并 {len(crawled_contents)} 个页面的内容...\n")
    
    merged_content = ""
    for item in crawled_contents:
        merged_content += f"\n\n{'='*60}\n"
        merged_content += f"来源: {item['url']}\n"
        merged_content += f"标题: {item['title']}\n"
        merged_content += f"{'='*60}\n\n"
        merged_content += item['content']
    
    # 第三步：用大模型生成总结
    sys.stderr.write(f"\n🤖 调用大模型生成总结...\n")
    
    # 加载环境变量
    LLMClientFactory.load_env_config()
    
    # 创建客户端（设置更长的超时时间，用于处理长内容）
    llm_client = LLMClientFactory.create_client(
        provider=llm_provider,
        model_name=llm_model,
        timeout=300  # 5分钟超时，足够处理长内容
    )
    
    # 构建提示词
    if summary_prompt is None:
        summary_prompt = f"""你是一个专业的内容总结助手。我爬取了以下 {len(crawled_contents)} 个网页的内容，请帮我：

1. 分析每个网页的核心内容
2. 提取关键信息和要点
3. 生成一份结构化的总结报告
4. 保持Markdown格式，使用清晰的标题和列表

网页内容：

{merged_content}

请输出总结报告："""
    else:
        summary_prompt = summary_prompt.replace("{content}", merged_content)
        summary_prompt = summary_prompt.replace("{count}", str(len(crawled_contents)))
    
    # 调用大模型
    messages = [{"role": "user", "content": summary_prompt}]
    start_time = time.time()
    result = llm_client.chat_completion(messages)
    end_time = time.time()
    
    if result.get("error"):
        return f"❌ 大模型调用失败: {result['error']}"
    
    summary_content = result.get("content", "")
    
    # 第四步：保存总结报告
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    summary_file = target_dir / f"总结报告_{timestamp}.md"
    
    # 添加元信息
    summary_report = f"""# 网页内容总结报告

生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
大模型: {result['provider']} - {result['model']}
处理耗时: {end_time - start_time:.2f} 秒
Token使用: {result.get('usage', {}).get('total_tokens', 'N/A')}

## 原始URL列表

"""
    
    for i, item in enumerate(crawled_contents, 1):
        summary_report += f"{i}. [{item['title']}]({item['url']})\n"
    
    if failed_urls:
        summary_report += "\n### 爬取失败的URL\n\n"
        for url in failed_urls:
            summary_report += f"• {url}\n"
    
    summary_report += f"\n{'='*60}\n\n"
    summary_report += summary_content
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary_report)
    
    # 返回结果
    result_info = f"""✅ 批量爬取+总结完成！

{'='*60}
📊 处理统计
{'='*60}
• 总URL数: {len(urls)}
• 成功爬取: {len(crawled_contents)}
• 失败: {len(failed_urls)}
• 大模型: {result['provider']} - {result['model']}
• 生成耗时: {end_time - start_time:.2f} 秒
• Token使用: {result.get('usage', {}).get('total_tokens', 'N/A')}

{'='*60}
📁 文件信息
{'='*60}
• 总结报告: {summary_file}
• 原始文件: {'已保存' if save_originals else '未保存'}
• 输出目录: {target_dir}
• 图片目录: {target_dir / img_folder}

{'='*60}
📝 总结预览
{'='*60}
{summary_content[:500]}...

"""
    
    return result_info

@mcp.tool()
def diagnose_crawl_failure(url: str, verbose: bool = True) -> str:
    """
    诊断网页爬取失败的原因
    
    Args:
        url: 要诊断的网页URL
        verbose: 是否输出详细日志
        
    Returns:
        包含详细诊断信息的字符串
    """
    import sys
    import requests
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup
    
    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"🔍 诊断爬取失败原因: {url}\n")
    sys.stderr.write(f"{'='*60}\n\n")
    
    diagnosis = []
    
    # 1. 基本连通性测试
    sys.stderr.write("1️⃣ 测试基本连通性...\n")
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        diagnosis.append(f"✓ HTTP状态码: {response.status_code}")
        
        if response.status_code != 200:
            diagnosis.append(f"⚠️ 状态码异常（非200），这可能导致爬取失败")
            
        diagnosis.append(f"✓ 最终URL: {response.url}")
        if response.url != url:
            diagnosis.append(f"ℹ️ 发生了重定向")
            
    except requests.exceptions.Timeout:
        diagnosis.append("❌ 连接超时 - 网站响应太慢或无法访问")
        return "\n".join(diagnosis)
    except requests.exceptions.ConnectionError:
        diagnosis.append("❌ 连接失败 - 网站可能不存在或网络问题")
        return "\n".join(diagnosis)
    except Exception as e:
        diagnosis.append(f"❌ 请求失败: {e}")
        return "\n".join(diagnosis)
    
    # 2. 检查网站配置
    sys.stderr.write("\n2️⃣ 检查网站配置...\n")
    site_config = get_site_config(url)
    domain = urlparse(url).netloc
    
    diagnosis.append(f"\n📋 网站配置 ({domain}):")
    diagnosis.append(f"  • 需要JS渲染: {'是' if site_config.get('needs_js') else '否'}")
    diagnosis.append(f"  • 需要Cookies: {'是' if site_config.get('needs_cookies') else '否'}")
    diagnosis.append(f"  • 内容选择器: {len(site_config.get('main_content_selectors', []))} 个")
    
    # 3. 分析HTML结构
    sys.stderr.write("\n3️⃣ 分析HTML结构...\n")
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        html_text = response.text
        
        diagnosis.append(f"\n📄 HTML分析:")
        diagnosis.append(f"  • 文档长度: {len(html_text)} 字符")
        diagnosis.append(f"  • 标题: {soup.title.string if soup.title else '无标题'}")
        
        # 检查是否是SPA
        has_app_div = bool(soup.select_one('#app'))
        has_root_div = bool(soup.select_one('#root'))
        is_vite = 'vite' in html_text.lower() or 'vitepress' in html_text.lower()
        
        if has_app_div or has_root_div or is_vite:
            diagnosis.append(f"  ⚠️ 检测到SPA特征（#app/#root/vite），需要JS渲染")
            diagnosis.append(f"     - #app存在: {has_app_div}")
            diagnosis.append(f"     - #root存在: {has_root_div}")
            diagnosis.append(f"     - Vite标识: {is_vite}")
        
        # 检查内容选择器
        diagnosis.append(f"\n🎯 内容选择器匹配:")
        for selector in site_config.get('main_content_selectors', []):
            element = soup.select_one(selector)
            if element:
                text_len = len(element.get_text(strip=True))
                diagnosis.append(f"  ✓ {selector}: {text_len} 字符")
            else:
                diagnosis.append(f"  ✗ {selector}: 未找到")
        
    except Exception as e:
        diagnosis.append(f"  ❌ HTML解析失败: {e}")
    
    # 4. 给出建议
    sys.stderr.write("\n4️⃣ 生成建议...\n")
    diagnosis.append(f"\n💡 建议:")
    
    if site_config.get('needs_js'):
        diagnosis.append("  • 该网站需要JS渲染，确保已安装Playwright")
        diagnosis.append("  • 运行: pip install playwright && playwright install chromium")
    
    if site_config.get('needs_cookies'):
        diagnosis.append("  • 该网站需要登录，请提供cookies文件")
    
    if response.status_code != 200:
        diagnosis.append(f"  • HTTP状态码异常({response.status_code})，检查URL是否正确")
    
    if len(html_text) < 3000:
        diagnosis.append("  • HTML内容过少，可能需要JS渲染或登录")
    
    diagnosis.append("\n  • 使用 verbose=True 参数获取更详细的日志")
    diagnosis.append("  • 使用 max_retries 参数增加重试次数")
    
    return "\n".join(diagnosis)

if __name__ == "__main__":
    mcp.run()

