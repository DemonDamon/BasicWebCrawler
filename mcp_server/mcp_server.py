#!/usr/bin/env python3
"""
BasicWebCrawler MCP Server

基于FastMCP的MCP服务器，提供网页爬虫功能，支持：
- 单个URL爬取并转换为Markdown
- 从文本中提取URL并批量爬取
- 图片下载和本地化
- 多种网站特定配置支持
- 大模型二次生成内容（整理、翻译、格式化等）
"""

import asyncio
import json
import os
import sys
import time
import tempfile
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from pathlib import Path
from contextlib import redirect_stdout

# 自定义日志过滤器，过滤 FastMCP 的启动日志
class FastMCPLogFilter(logging.Filter):
    """过滤 FastMCP 框架的 INFO 级别日志"""
    def filter(self, record):
        # 过滤包含这些关键词的日志
        skip_keywords = [
            "Starting MCP server",
            "Processing request of type",
            "ListToolsRequest",
            "ListPromptsRequest",
            "ListResourcesRequest"
        ]
        message = record.getMessage()
        return not any(keyword in message for keyword in skip_keywords)

# 配置日志 - 使用 INFO 级别，避免被标记为错误
# 注意：在导入 FastMCP 之前设置日志级别，以抑制框架的 INFO 日志

# 设置环境变量，抑制 FastMCP 的详细日志
os.environ.setdefault("MCP_LOG_LEVEL", "WARNING")
os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")

# 创建自定义 handler，添加过滤器
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(logging.Formatter('%(message)s'))
stderr_handler.addFilter(FastMCPLogFilter())

logging.basicConfig(
    level=logging.WARNING,  # 先设置为 WARNING，避免 FastMCP 的 INFO 日志
    format='%(message)s',
    handlers=[stderr_handler],
    force=True  # 强制重新配置，覆盖之前的配置
)

# 抑制 FastMCP 框架的 INFO 级别日志（避免显示 "Processing request" 等）
# 尝试所有可能的 logger 名称
for logger_name in [
    "mcp", "fastmcp", "mcp.server", "mcp.server.server", 
    "fastmcp.server", "fastmcp.server.server",
    "__main__", "rich", "rich.logging"
]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
    logging.getLogger(logger_name).propagate = False  # 阻止传播到父 logger

# 创建我们自己的 logger，使用 INFO 级别
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# 为我们的 logger 添加 handler
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

# 设置 crawler 模块的 logger
try:
    from crawler import set_crawler_logger
    set_crawler_logger(logger)
except ImportError:
    pass

# 添加父目录到Python路径，以便导入crawler模块
sys.path.append(str(Path(__file__).parent.parent))

from fastmcp import FastMCP
from crawler import (
    fetch_and_convert_to_markdown,
    fetch_with_retry,
    process_url_text_mode,
    convert_html_to_markdown,
    convert_html_to_text,
    render_with_actions,
    render_with_actions_threaded,
    extract_metadata_and_external,
    collect_links,
    images_summary,
    links_summary,
    DiskCache,
    extract_urls_from_text,
    get_site_config,
    sanitize_filename
)

# 设置环境变量，标识当前在 MCP 模式下运行
# 这样 llm_client.py 就能正确配置日志，避免 INFO 日志输出到 stderr
os.environ["MCP_MODE"] = "true"

# 导入大模型客户端
try:
    from llm_client import LLMClientFactory
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    # 不使用 print，因为会干扰 MCP 的 JSON-RPC 通信
    import sys
    sys.stderr.write("⚠️ 警告: llm_client.py 不可用，大模型功能将被禁用\n")

# 创建FastMCP服务器实例
mcp = FastMCP("BasicWebCrawler")

@mcp.tool()
def crawl_single_url(
    url: str,
    img_folder: str = "images",
    use_cookies: bool = False,
    cookies_file: Optional[str] = None,
    output_dir: Optional[str] = None,
    max_retries: int = 2,
    verbose: bool = False
) -> str:
    """
    爬取单个网页并转换为Markdown格式
    
    Args:
        url: 要爬取的网页URL
        img_folder: 图片保存文件夹路径，默认为"images"
        use_cookies: 是否使用cookies文件
        cookies_file: cookies文件路径（JSON格式）
        output_dir: 输出目录路径
        max_retries: 最大重试次数（默认2次）
        verbose: 是否输出详细调试日志
        
    Returns:
        包含爬取结果信息的字符串
    """
    try:
        # 记录调试信息
        debug_info = {
            'url': url,
            'domain': urlparse(url).netloc,
            'retries_used': 0,
            'js_rendered': False,
            'selector_used': None
        }
        # 自动检测项目根目录下的cookies文件
        if not cookies_file:
            project_root = Path(__file__).parent.parent
            default_cookies = project_root / 'zhihu_cookies.json'
            if default_cookies.exists():
                cookies_file = str(default_cookies)
                use_cookies = True

        # 处理cookies
        cookies = None
        if use_cookies and cookies_file and os.path.exists(cookies_file):
            try:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
            except Exception as e:
                return f"读取cookies文件失败: {str(e)}"
        
        # 检查网站配置
        site_config = get_site_config(url)
        debug_info['needs_cookies'] = site_config.get('needs_cookies', False)
        debug_info['needs_js'] = site_config.get('needs_js', False)
        
        if site_config['needs_cookies'] and not cookies:
            return f"⚠️ 警告: 网站 {debug_info['domain']} 可能需要cookies才能正常访问。\n建议使用 cookies_file 参数提供cookies。\n\n将尝试继续爬取..."
        
        project_root = Path(__file__).parent.parent
        target_dir = Path(output_dir).resolve() if output_dir else project_root
        target_dir.mkdir(parents=True, exist_ok=True)
        img_dir = str(target_dir / img_folder)
        old_cwd = os.getcwd()
        os.chdir(str(target_dir))
        try:
            with redirect_stdout(sys.stderr):
                start_time = time.time()
                # 使用带重试机制的爬取函数
                markdown_output, page_title = fetch_with_retry(
                    url, 
                    img_folder=img_dir, 
                    cookies=cookies,
                    max_retries=max_retries,
                    verbose=verbose
                )
                end_time = time.time()
                debug_info['retries_used'] = max_retries if markdown_output is None else 1
        finally:
            os.chdir(old_cwd)
        
        if markdown_output:
            sanitized_title = sanitize_filename(page_title)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"{sanitized_title}_{timestamp}.md"
            try:
                output_path = target_dir / output_file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                
                # 统计信息
                content_length = len(markdown_output)
                img_count = markdown_output.count('![')
                
                result = f"✅ 爬取成功！\n\n" \
                       f"📄 页面标题: {page_title}\n" \
                       f"🔗 URL: {url}\n" \
                       f"📁 保存文件: {output_path}\n" \
                       f"📊 内容长度: {content_length} 字符\n" \
                       f"🖼️ 图片数量: {img_count} 张\n" \
                       f"🖼️ 图片目录: {img_dir}/\n" \
                       f"⏱️ 耗时: {end_time - start_time:.2f} 秒\n"
                
                if verbose:
                    result += f"\n🔍 调试信息:\n"
                    result += f"• 站点域名: {debug_info['domain']}\n"
                    result += f"• 需要JS: {debug_info['needs_js']}\n"
                    result += f"• 需要Cookies: {debug_info['needs_cookies']}\n"
                    result += f"• 重试次数: {debug_info['retries_used']}\n"
                
                result += f"\n内容预览:\n{markdown_output[:500]}..."
                return result
                       
            except OSError as e:
                # 使用备用文件名
                fallback_filename = f"webpage_{timestamp}.md"
                fallback_path = target_dir / fallback_filename
                with open(fallback_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                return f"✅ 爬取成功（使用备用文件名）！\n文件: {fallback_filename}\n耗时: {end_time - start_time:.2f} 秒"
        else:
            # 提供详细的失败信息
            error_msg = f"❌ 爬取失败: 无法获取网页内容\n\n"
            error_msg += f"🔍 调试信息:\n"
            error_msg += f"• URL: {url}\n"
            error_msg += f"• 域名: {debug_info['domain']}\n"
            error_msg += f"• 需要JS: {debug_info['needs_js']}\n"
            error_msg += f"• 需要Cookies: {debug_info['needs_cookies']}\n"
            error_msg += f"• 重试次数: {max_retries}\n\n"
            error_msg += f"💡 建议:\n"
            
            if debug_info['needs_cookies']:
                error_msg += "• 该网站可能需要cookies，请尝试提供 cookies_file 参数\n"
            if debug_info['needs_js']:
                error_msg += "• 该网站需要JS渲染，已自动使用Playwright\n"
            
            error_msg += "• 请检查URL是否正确或网站是否可访问\n"
            error_msg += f"• 尝试设置 verbose=True 获取更多调试信息"
            
            return error_msg
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc() if verbose else str(e)
        return f"❌ 爬取过程中发生异常: {error_trace}"

@mcp.tool()
def crawl_urls_from_text(
    text: str,
    img_folder: str = "images",
    use_cookies: bool = False,
    cookies_file: Optional[str] = None,
    output_dir: Optional[str] = None
) -> str:
    """
    从文本中提取URL并批量爬取
    
    Args:
        text: 包含URL的文本内容
        img_folder: 图片保存文件夹路径，默认为"images"
        use_cookies: 是否使用cookies文件
        cookies_file: cookies文件路径（JSON格式）
        
    Returns:
        包含批量爬取结果的字符串
    """
    try:
        # 自动检测项目根目录下的cookies文件
        if not cookies_file:
            project_root = Path(__file__).parent.parent
            default_cookies = project_root / 'zhihu_cookies.json'
            if default_cookies.exists():
                cookies_file = str(default_cookies)
                use_cookies = True

        # 处理cookies
        cookies = None
        if use_cookies and cookies_file and os.path.exists(cookies_file):
            try:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
            except Exception as e:
                return f"读取cookies文件失败: {str(e)}"
        
        # 提取URL
        urls = extract_urls_from_text(text)
        if not urls:
            return "❌ 未在提供的文本中找到任何有效的URL"
        
        project_root = Path(__file__).parent.parent
        target_dir = Path(output_dir).resolve() if output_dir else project_root
        target_dir.mkdir(parents=True, exist_ok=True)
        img_dir = str(target_dir / img_folder)
        old_cwd = os.getcwd()
        os.chdir(str(target_dir))
        try:
            with redirect_stdout(sys.stderr):
                start_time = time.time()
                markdown_output, result_summary = process_url_text_mode(text, img_dir, cookies)
                end_time = time.time()
        finally:
            os.chdir(old_cwd)
        
        if markdown_output:
            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"批量爬取结果_{timestamp}.md"
            try:
                output_path = target_dir / output_file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                return f"✅ 批量爬取完成！\n\n" \
                       f"📊 {result_summary}\n" \
                       f"📁 保存文件: {output_path}\n" \
                       f"🖼️ 图片目录: {img_dir}/\n" \
                       f"⏱️ 总耗时: {end_time - start_time:.2f} 秒\n\n" \
                       f"发现的URL:\n" + "\n".join([f"• {url}" for url in urls])
                       
            except OSError as e:
                fallback_filename = f"批量爬取_{timestamp}.md"
                fallback_path = target_dir / fallback_filename
                with open(fallback_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                return f"✅ 批量爬取完成（使用备用文件名）！\n文件: {fallback_filename}"
        else:
            return f"❌ 批量爬取失败: 未能成功处理任何URL"
            
    except Exception as e:
        return f"❌ 批量爬取过程中发生错误: {str(e)}"

@mcp.tool()
def extract_urls(text: str) -> str:
    """
    从文本中提取URL列表
    
    Args:
        text: 要分析的文本内容
        
    Returns:
        提取到的URL列表和统计信息
    """
    try:
        urls = extract_urls_from_text(text)
        
        if not urls:
            return "❌ 未在文本中找到任何有效的URL"
        
        result = f"✅ 成功提取到 {len(urls)} 个URL:\n\n"
        for i, url in enumerate(urls, 1):
            # 获取网站配置信息
            site_config = get_site_config(url)
            domain = urlparse(url).netloc
            needs_cookies = "🔐 需要cookies" if site_config['needs_cookies'] else "🔓 无需cookies"
            
            result += f"{i}. {url}\n"
            result += f"   域名: {domain} | {needs_cookies}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ URL提取过程中发生错误: {str(e)}"

@mcp.tool()
def check_site_config(url: str) -> str:
    """
    检查网站的特定配置信息
    
    Args:
        url: 要检查的网站URL
        
    Returns:
        网站配置信息
    """
    try:
        site_config = get_site_config(url)
        domain = urlparse(url).netloc
        
        result = f"🌐 网站配置信息 - {domain}\n\n"
        result += f"🔐 需要cookies: {'是' if site_config['needs_cookies'] else '否'}\n"
        result += f"🎯 内容选择器: {', '.join(site_config['main_content_selectors'])}\n"
        result += f"📋 请求头数量: {len(site_config['headers'])}\n\n"
        
        result += "📋 请求头详情:\n"
        for key, value in site_config['headers'].items():
            result += f"  • {key}: {value}\n"
        
        return result
        
    except Exception as e:
        return f"❌ 检查网站配置时发生错误: {str(e)}"

@mcp.tool()
def get_supported_sites() -> str:
    """
    获取支持的网站列表和配置信息
    
    Returns:
        支持的网站列表
    """
    try:
        from crawler import SITE_CONFIGS
        
        result = "🌐 支持的网站配置:\n\n"
        
        for site, config in SITE_CONFIGS.items():
            if site == 'default':
                continue
                
            result += f"🔗 {site}\n"
            result += f"   🔐 需要cookies: {'是' if config['needs_cookies'] else '否'}\n"
            result += f"   🎯 内容选择器: {len(config['main_content_selectors'])} 个\n"
            result += f"   📋 自定义请求头: {len(config['headers'])} 个\n\n"
        
        result += "📝 说明:\n"
        result += "• 支持的网站有专门优化的内容提取配置\n"
        result += "• 其他网站将使用通用配置进行爬取\n"
        result += "• 需要cookies的网站建议提供cookies文件以获得更好的爬取效果\n"
        
        return result
        
    except Exception as e:
        return f"❌ 获取网站列表时发生错误: {str(e)}"

@mcp.resource("crawler://config")
def get_crawler_config():
    """
    提供爬虫的配置信息
    """
    try:
        from crawler import SITE_CONFIGS, IGNORED_EXTENSIONS
        
        config_info = {
            "supported_sites": list(SITE_CONFIGS.keys()),
            "ignored_image_extensions": IGNORED_EXTENSIONS,
            "default_image_folder": "images",
            "features": [
                "单个URL爬取",
                "批量URL提取和爬取",
                "图片下载和本地化",
                "多网站特定配置",
                "Cookies支持",
                "Markdown格式输出"
            ]
        }
        
        return json.dumps(config_info, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取配置信息时发生错误: {str(e)}"

@mcp.prompt()
def crawl_webpage_prompt(url: str, use_cookies: bool = False):
    """
    爬取网页的提示模板
    
    Args:
        url: 要爬取的网页URL
        use_cookies: 是否使用cookies
    """
    prompt_text = f"""我需要爬取这个网页的内容: {url}

请帮我：
1. 爬取网页内容并转换为Markdown格式
2. 下载并本地化所有图片
3. 提供爬取结果的详细信息

{'注意：如果这个网站需要登录，请确保提供有效的cookies文件。' if use_cookies else ''}

请使用 crawl_single_url 工具来完成这个任务。"""

    return prompt_text

@mcp.prompt()
def batch_crawl_prompt(text_content: str):
    """
    批量爬取的提示模板
    
    Args:
        text_content: 包含URL的文本内容
    """
    prompt_text = f"""我有一段包含多个URL的文本，需要批量爬取这些网页：

文本内容：
{text_content}

请帮我：
1. 从文本中提取所有有效的URL
2. 批量爬取每个URL的内容
3. 将所有内容合并到一个Markdown文件中
4. 提供详细的爬取统计信息

请使用 crawl_urls_from_text 工具来完成这个任务。"""

    return prompt_text

def main():
    mcp.run()

@mcp.tool()
def interactive_crawl(
    url: str,
    actions: List[Dict],
    img_folder: str = "images",
    output_dir: Optional[str] = None,
    use_cookies: bool = False,
    cookies_file: Optional[str] = None,
    headers: Optional[Dict] = None,
    headless: bool = False,
    timeout_ms: int = 15000,
    return_format: str = "markdown",
    no_cache: bool = False,
    retain_images: bool = True,
    no_gfm: bool = False,
    keep_img_data_url: bool = False,
    with_images_summary: bool = False,
    with_links_summary: bool = False
) -> str:
    try:
        # 自动检测项目根目录下的cookies文件
        if not cookies_file:
            project_root = Path(__file__).parent.parent
            default_cookies = project_root / 'zhihu_cookies.json'
            if default_cookies.exists():
                cookies_file = str(default_cookies)
                use_cookies = True

        cookies = None
        if use_cookies and cookies_file and os.path.exists(cookies_file):
            try:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
            except Exception as e:
                return f"读取cookies文件失败: {str(e)}"
        site_conf = get_site_config(url)
        merged_headers = {}
        merged_headers.update(site_conf.get('headers', {}))
        if headers:
            merged_headers.update(headers)
        project_root = Path(__file__).parent.parent
        target_dir = Path(output_dir).resolve() if output_dir else project_root
        target_dir.mkdir(parents=True, exist_ok=True)
        img_dir = str(target_dir / img_folder)
        old_cwd = os.getcwd()
        os.chdir(str(target_dir))
        cache = DiskCache()
        params_for_cache = {
            "actions": actions,
            "headers": merged_headers,
            "headless": headless,
            "timeout_ms": timeout_ms
        }
        html = None
        if not no_cache:
            key = cache.key_for(url, params_for_cache)
            html = cache.get(key)
        try:
            with redirect_stdout(sys.stderr):
                start_time = time.time()
                if html is None:
                    html = render_with_actions_threaded(url, actions, headers=merged_headers, cookies=cookies, headless=headless, timeout_ms=timeout_ms)
                    if html:
                        if not no_cache:
                            cache.set(cache.key_for(url, params_for_cache), html)
                if not html:
                    return "❌ 交互失败或无法获取页面内容"
                if return_format == "text":
                    content_output, page_title = convert_html_to_text(html, url)
                    file_ext = ".txt"
                else:
                    content_output, page_title = convert_html_to_markdown(html, url, img_dir, no_gfm=no_gfm, retain_images=retain_images, keep_img_data_url=keep_img_data_url)
                    file_ext = ".md"
                end_time = time.time()
        finally:
            os.chdir(old_cwd)
        if content_output:
            sanitized_title = sanitize_filename(page_title)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"{sanitized_title}_{timestamp}{file_ext}"
            try:
                output_path = target_dir / output_file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content_output)
                metadata, external, soup = extract_metadata_and_external(html)
                links = collect_links(soup, url) if soup else []
                result = {
                    "title": page_title,
                    "url": url,
                    "format": return_format,
                    "content": content_output,
                    "metadata": metadata,
                    "external": external,
                    "summaries": {},
                    "files": {
                        "output_path": str(output_path),
                        "images_dir": img_dir if not retain_images else None
                    },
                    "elapsed_seconds": round(end_time - start_time, 2)
                }
                if with_images_summary and not retain_images:
                    result["summaries"]["images"] = images_summary(img_dir)
                if with_links_summary:
                    result["summaries"]["links"] = links_summary(links)
                return json.dumps(result, ensure_ascii=False)
            except OSError:
                fallback_filename = f"interactive_{timestamp}.md"
                fallback_path = target_dir / fallback_filename
                with open(fallback_path, 'w', encoding='utf-8') as f:
                    f.write(content_output)
                return json.dumps({
                    "title": page_title,
                    "url": url,
                    "format": return_format,
                    "files": {"output_path": str(fallback_path), "images_dir": img_dir if not retain_images else None}
                }, ensure_ascii=False)
        else:
            return "❌ 转换失败"
    except Exception as e:
        return f"❌ 交互过程中发生错误: {str(e)}"

@mcp.tool()
def crawl_and_regenerate_with_llm(
    url: str = None,
    input_file: str = None,
    provider: str = "bailian",
    model_name: Optional[str] = None,
    prompt_template: Optional[str] = None,
    img_folder: str = "images",
    output_dir: Optional[str] = None,
    use_cookies: bool = False,
    cookies_file: Optional[str] = None,
    max_retries: int = 2,
    save_original: bool = True,
    language: str = "中文",
    stream: bool = True
) -> str:
    """
    爬取网页内容并使用大模型进行二次生成（整理、翻译、格式化等）
    
    Args:
        url: 要爬取的网页URL（与input_file二选一）
        input_file: 已有的Markdown文件路径（与url二选一，优先使用）
        provider: 大模型厂商，可选：siliconflow, deepseek, bailian, kimi（默认：deepseek）
        model_name: 模型名称，如果为None则使用厂商默认模型
        prompt_template: 自定义提示词模板，可以使用 {content} 作为占位符
        img_folder: 图片保存文件夹路径，默认为"images"
        output_dir: 输出目录路径
        use_cookies: 是否使用cookies文件
        cookies_file: cookies文件路径（JSON格式）
        max_retries: 最大重试次数（默认2次，当使用input_file时此参数无效）
        save_original: 是否同时保存原始爬取内容（默认True）
        language: 目标语言（默认：中文）
        stream: 是否使用流式输出（默认True），流式模式可以实时看到生成进度
        
    Returns:
        包含爬取和生成结果信息的字符串
    """
    if not LLM_AVAILABLE:
        return "❌ 错误: llm_client 模块不可用，请确保 llm_client.py 文件存在"
    
    if not url and not input_file:
        return "❌ 错误: 必须提供 url 或 input_file 参数之一"
    
    try:
        # 设置输出目录
        if output_dir:
            target_dir = Path(output_dir).resolve()
        else:
            target_dir = Path.cwd()
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 第一步：获取内容
        if input_file:
            # 使用已有文件
            import sys
            
            input_path = Path(input_file)
            if not input_path.exists():
                return f"❌ 文件不存在: {input_file}"
            
            with open(input_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            page_title = input_path.stem
            md_file_path = input_path
            
        else:
            # 爬取网页内容
            import sys
            
            # 处理 cookies
            cookies = None
            if use_cookies and cookies_file and os.path.exists(cookies_file):
                try:
                    with open(cookies_file, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)
                except Exception as e:
                    return f"❌ 读取cookies文件失败: {str(e)}"
            
            # 使用 crawler.py 的核心函数直接爬取
            img_dir = str(target_dir / img_folder)
            
            try:
                # 调用爬取函数
                markdown_output, page_title = fetch_and_convert_to_markdown(
                    url=url,
                    img_folder=img_dir,
                    cookies=cookies,
                    verbose=False
                )
            except Exception as e:
                return f"❌ 爬取失败: {str(e)}"
            
            if not markdown_output:
                return "❌ 爬取失败: 未能获取网页内容"
            
            # 保存原始爬取内容
            sanitized_title = sanitize_filename(page_title)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            original_filename = f"{sanitized_title}_{timestamp}.md"
            md_file_path = target_dir / original_filename
            
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            
            original_content = markdown_output
        
        # 第二步：使用大模型进行二次生成
        import sys
        
        # 加载环境变量
        LLMClientFactory.load_env_config()
        
        # 创建大模型客户端（设置更长的超时时间，用于处理长内容）
        try:
            llm_client = LLMClientFactory.create_client(
                provider=provider,
                model_name=model_name,
                timeout=300  # 5分钟超时，足够处理长内容
            )
        except Exception as e:
            return f"❌ 创建大模型客户端失败: {str(e)}\n\n请检查：\n1. API密钥是否正确配置\n2. 厂商名称是否正确（支持: siliconflow, deepseek, bailian, kimi）\n3. 模型名称是否有效"
        
        # 构建提示词
        if prompt_template is None:
            # 默认提示词模板
            prompt_template = f"""你是一个专业的内容整理助手。我给你一份从网页爬取的Markdown格式内容，请帮我：

1. 整理和优化内容结构，使其更清晰易读
2. 翻译成{language}（如果原内容不是{language}）
3. 保留所有重要信息和链接
4. 保持Markdown格式
5. 适当添加章节标题和段落划分

原始内容：

{{content}}

请输出整理后的Markdown内容："""
        
        # 替换占位符
        final_prompt = prompt_template.replace("{content}", original_content)
        
        # 调用大模型
        messages = [{"role": "user", "content": final_prompt}]
        
        start_time = time.time()
        result = llm_client.chat_completion(messages, stream=stream)
        end_time = time.time()
        
        # 防御性检查：确保 result 不为 None
        if result is None:
            return f"❌ 大模型调用失败: 返回结果为空"
        
        if result.get("error"):
            return f"❌ 大模型调用失败: {result['error']}"
        
        regenerated_content = result.get("content", "")
        
        if not regenerated_content:
            return f"❌ 大模型返回空内容"
        
        # 保存二次生成的内容
        base_path = Path(md_file_path)
        regenerated_file_path = base_path.parent / f"{base_path.stem}_regenerated.md"
        
        with open(regenerated_file_path, 'w', encoding='utf-8') as f:
            f.write(regenerated_content)
        
        # 如果不需要保存原始内容，可以删除
        if not save_original and input_file is None:  # 只有当内容是刚爬取的才删除
            os.remove(md_file_path)
            original_status = "已删除"
        else:
            original_status = str(md_file_path)
        
        # 构建返回信息
        # 防御性检查：确保 result 中的字段存在
        provider_name = result.get('provider', 'Unknown')
        model_name_result = result.get('model', 'Unknown')
        usage_info = result.get('usage', {})
        total_tokens = usage_info.get('total_tokens', 'N/A') if isinstance(usage_info, dict) else 'N/A'
        
        result_info = f"""✅ {'内容重写' if input_file else '爬取并重写'}成功！

{'='*60}
📊 处理统计
{'='*60}
{'🔗 URL: ' + url if url else '📄 输入文件: ' + input_file}
📄 页面标题: {page_title}
🏢 大模型厂商: {provider_name}
🤖 模型: {model_name_result}
📝 原始内容: {len(original_content)} 字符
📝 生成内容: {len(regenerated_content)} 字符
⏱️  生成耗时: {end_time - start_time:.2f} 秒
💰 Token使用: {total_tokens}

{'='*60}
📁 文件信息
{'='*60}
📄 原始文件: {original_status}
📄 生成文件: {regenerated_file_path}
{'🖼️  图片目录: ' + str(target_dir / img_folder) if not input_file else ''}

{'='*60}
🎯 提示
{'='*60}
- 生成的内容已保存到新文件中
- 可以通过 save_original=False 参数删除原始文件（仅限爬取模式）
- 可以通过 prompt_template 参数自定义生成提示词
- 支持的厂商: siliconflow, deepseek, bailian, kimi
"""
        
        return result_info
        
    except Exception as e:
        return f"❌ 处理过程中发生错误: {str(e)}\n\n错误类型: {type(e).__name__}"

@mcp.prompt()
def llm_regenerate_prompt(url: str, task_description: str = "整理和翻译成中文"):
    """
    大模型二次生成的提示模板
    
    Args:
        url: 要处理的网页URL
        task_description: 任务描述
    """
    prompt_text = f"""我需要爬取并使用大模型处理这个网页：{url}

任务要求：
{task_description}

请使用 crawl_and_regenerate_with_llm 工具来：
1. 爬取网页内容并转换为Markdown格式
2. 使用大模型对内容进行二次生成和整理
3. 保存处理后的结果

你可以自定义：
- provider: 选择大模型厂商（siliconflow/deepseek/bailian/kimi）
- prompt_template: 自定义处理提示词
- language: 目标语言（默认中文）
"""
    return prompt_text

if __name__ == "__main__":
    main()
