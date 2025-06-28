#!/usr/bin/env python3
"""
BasicWebCrawler MCP Server

基于FastMCP的MCP服务器，提供网页爬虫功能，支持：
- 单个URL爬取并转换为Markdown
- 从文本中提取URL并批量爬取
- 图片下载和本地化
- 多种网站特定配置支持
"""

import asyncio
import json
import os
import sys
import time
import tempfile
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from pathlib import Path

# 添加父目录到Python路径，以便导入crawler模块
sys.path.append(str(Path(__file__).parent.parent))

from fastmcp import FastMCP
from crawler import (
    fetch_and_convert_to_markdown,
    process_url_text_mode,
    extract_urls_from_text,
    get_site_config,
    sanitize_filename
)

# 创建FastMCP服务器实例
mcp = FastMCP("BasicWebCrawler")

@mcp.tool()
def crawl_single_url(
    url: str,
    img_folder: str = "images",
    use_cookies: bool = False,
    cookies_file: Optional[str] = None
) -> str:
    """
    爬取单个网页并转换为Markdown格式
    
    Args:
        url: 要爬取的网页URL
        img_folder: 图片保存文件夹路径，默认为"images"
        use_cookies: 是否使用cookies文件
        cookies_file: cookies文件路径（JSON格式）
        
    Returns:
        包含爬取结果信息的字符串
    """
    try:
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
        if site_config['needs_cookies'] and not cookies:
            return f"警告: 网站 {urlparse(url).netloc} 可能需要cookies才能正常访问。建议使用cookies参数。"
        
        # 开始爬取
        start_time = time.time()
        markdown_output, page_title = fetch_and_convert_to_markdown(url, img_folder, cookies)
        end_time = time.time()
        
        if markdown_output:
            # 生成文件名
            sanitized_title = sanitize_filename(page_title)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"{sanitized_title}_{timestamp}.md"
            
            # 保存文件到项目根目录
            try:
                # 获取项目根目录路径
                project_root = Path(__file__).parent.parent
                output_path = project_root / output_file
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                
                return f"✅ 爬取成功！\n\n" \
                       f"📄 页面标题: {page_title}\n" \
                       f"🔗 URL: {url}\n" \
                       f"📁 保存文件: {output_file}\n" \
                       f"🖼️ 图片目录: {img_folder}/\n" \
                       f"⏱️ 耗时: {end_time - start_time:.2f} 秒\n\n" \
                       f"内容预览:\n{markdown_output[:500]}..."
                       
            except OSError as e:
                # 使用备用文件名
                fallback_filename = f"webpage_{timestamp}.md"
                project_root = Path(__file__).parent.parent
                fallback_path = project_root / fallback_filename
                with open(fallback_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                return f"✅ 爬取成功（使用备用文件名）！\n文件: {fallback_filename}\n耗时: {end_time - start_time:.2f} 秒"
        else:
            return f"❌ 爬取失败: 无法获取网页内容，请检查URL是否正确或网站是否可访问"
            
    except Exception as e:
        return f"❌ 爬取过程中发生错误: {str(e)}"

@mcp.tool()
def crawl_urls_from_text(
    text: str,
    img_folder: str = "images",
    use_cookies: bool = False,
    cookies_file: Optional[str] = None
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
        
        # 开始批量爬取
        start_time = time.time()
        markdown_output, result_summary = process_url_text_mode(text, img_folder, cookies)
        end_time = time.time()
        
        if markdown_output:
            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"批量爬取结果_{timestamp}.md"
            
            # 保存文件到项目根目录
            try:
                # 获取项目根目录路径
                project_root = Path(__file__).parent.parent
                output_path = project_root / output_file
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_output)
                
                return f"✅ 批量爬取完成！\n\n" \
                       f"📊 {result_summary}\n" \
                       f"📁 保存文件: {output_file}\n" \
                       f"🖼️ 图片目录: {img_folder}/\n" \
                       f"⏱️ 总耗时: {end_time - start_time:.2f} 秒\n\n" \
                       f"发现的URL:\n" + "\n".join([f"• {url}" for url in urls])
                       
            except OSError as e:
                fallback_filename = f"批量爬取_{timestamp}.md"
                project_root = Path(__file__).parent.parent
                fallback_path = project_root / fallback_filename
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
    """运行MCP服务器"""
    mcp.run()

if __name__ == "__main__":
    main() 