import requests
from bs4 import BeautifulSoup, NavigableString
import markdownify
import os
import urllib.parse
import re
from urllib.parse import urljoin, urlparse
import hashlib
import time
import json
import tempfile
import contextlib
import argparse
import threading
import queue
try:
    import browser_cookie3
except ImportError:
    browser_cookie3 = None

# JS 渲染支持（可选）
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

# 不需要下载的图片格式
IGNORED_EXTENSIONS = ['.ico', '.webp', '.svg', '.gif', '.bmp', '.tiff']

# 网站特定配置
SITE_CONFIGS = {
    'mineru.net': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6',
            'Referer': 'https://mineru.net/',
        },
        # 常见的文档站（VitePress/VuePress/Docusaurus）内容区选择器
        'main_content_selectors': [
            'main',
            '.theme-default-content',
            '.content__default',
            '.theme-container .page .content',
            'div.VPDoc .VPDocContent',
            '#app',
        ],
        'wait_selectors': ['.theme-default-content', '.content__default', 'main'],
        'needs_cookies': False,
        'needs_js': True,
    },
    'zhihu.com': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.zhihu.com',
            'sec-ch-ua': '"Google Chrome";v="91", "Chromium";v="91"',
        },
        'main_content_selectors': ['div.Post-RichText', 'div.RichText', 'div.Post-content'],
        'needs_cookies': True,
        'needs_js': True
    },
    'bilibili.com': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.bilibili.com',
            'sec-ch-ua': '"Google Chrome";v="91", "Chromium";v="91"',
        },
        'main_content_selectors': ['.video-info-container', '.content-container', '.video-desc-container', '.player-wrapper'],
        'needs_cookies': False
    },
    'aibase.com': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.aibase.com',
        },
        'main_content_selectors': ['.container', '.tool-container', '.content-wrapper', 'main', 'article'],
        'needs_cookies': False
    },
    'ragas.org.cn': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://docs.ragas.org.cn/',
        },
        # Material for MkDocs 内容选择器
        'main_content_selectors': [
            'main article',
            'main .md-content',
            'main .md-content__inner',
            '.md-content',
            'article',
            'main'
        ],
        'needs_cookies': False,
        'needs_js': True,  # Material for MkDocs 可能需要JS渲染
        'wait_selectors': ['main article', '.md-content', 'main']
    },
    'hf-mirror.com': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        # 注意：不要把article放在前面，因为页面底部的Collection卡片也是article标签
        # 优先选择包含多个h2的main区域
        'main_content_selectors': ['main', 'div.container', '.prose', 'div[class*="prose"]'],
        'needs_cookies': False,
        'needs_js': True,
        'wait_selectors': ['h2', 'p']
    },
    'huggingface.co': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'main_content_selectors': ['main', 'div.container', '.prose', 'div[class*="prose"]'],
        'needs_cookies': False,
        'needs_js': True,
        'wait_selectors': ['h2', 'p']
    },
    'default': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        },
        # main应该优先于article，因为article可能是页面中的小组件
        'main_content_selectors': ['main', 'article', '.main-content', '.post-content', '.entry-content', '.content', '#content'],
        'needs_cookies': False
    }
}

def should_render_with_js(url, soup, response_text):
    """
    判断是否需要使用JS渲染：
    - 站点被标记为需要JS（如 mineru.net）
    - HTML过于稀薄或包含典型的SPA占位元素（#app、#root）
    """
    domain = urlparse(url).netloc
    site_conf = None
    for site_domain, conf in SITE_CONFIGS.items():
        if site_domain in domain:
            site_conf = conf
            break

    if site_conf and site_conf.get('needs_js'):
        return True

    # 内容很少且存在SPA占位符，或明显的VitePress/VuePress构建标识
    text_len = len(response_text or '')
    if text_len < 3000:
        if soup.select_one('#app') or soup.select_one('#root'):
            return True
        # Vite/VitePress 的常见关键字
        if 'vite' in (response_text or '').lower() or 'vitepress' in (response_text or '').lower():
            return True

    return False

def render_page_with_playwright(url, headers=None, cookies=None, wait_selectors=None, timeout_ms=15000):
    """
    使用 Playwright 渲染页面并返回完整的HTML。
    - headers 会作为额外请求头设置
    - cookies 可用于需要登录的站点
    - wait_selectors 若提供，将等待其中任一选择器出现后再返回内容
    """
    if sync_playwright is None:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 注入反检测脚本
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            if headers:
                context.set_extra_http_headers(headers)

            # 可选：添加 cookies（需要符合 Playwright cookie 结构）
            if cookies:
                with contextlib.suppress(Exception):
                    context.add_cookies(cookies)

            page = context.new_page()
            page.goto(url, wait_until='networkidle')

            # 如果提供了等待选择器，等待其中之一出现
            if wait_selectors:
                for sel in wait_selectors:
                    with contextlib.suppress(Exception):
                        page.wait_for_selector(sel, timeout=timeout_ms)
                        break
            
            # 额外等待2秒，确保动态内容完全加载（特别是React应用）
            page.wait_for_timeout(2000)

            content = page.content()
            context.close()
            browser.close()
            return content
    except Exception as e:
        print(f"Playwright 渲染失败: {e}")
        return None

def sanitize_filename(filename):
    """
    清理文件名，移除不允许的字符
    """
    # 确保文件名不为None
    if filename is None:
        return "untitled"
    
    # 替换换行符和制表符
    filename = filename.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # 替换Windows和Unix系统不允许的字符
    invalid_chars = r'[\\/*?:"<>|]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # 替换多个连续空格为单个空格
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # 限制长度，避免文件名过长
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + '...'
    
    # 移除前后空白
    sanitized = sanitized.strip()
    
    # 确保文件名不为空
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized

def should_download_image(img_url):
    """
    判断图片是否需要下载
    """
    # 检查URL扩展名
    parsed_url = urllib.parse.urlparse(img_url)
    path = parsed_url.path.lower()
    
    # 检查是否是忽略的扩展名
    for ext in IGNORED_EXTENSIONS:
        if path.endswith(ext):
            print(f"跳过下载: {img_url} (忽略的格式: {ext})")
            return False
    
    return True

def download_image(img_url, base_url, img_folder):
    """
    下载图片并返回本地路径
    """
    try:
        # 处理相对URL
        if not img_url.startswith(('http://', 'https://')):
            img_url = urljoin(base_url, img_url)
        
        # 检查是否应该下载此图片
        if not should_download_image(img_url):
            return None
        
        # 创建图片文件名 (使用URL的哈希值作为文件名，避免文件名冲突)
        img_hash = hashlib.md5(img_url.encode()).hexdigest()
        
        # 获取原始扩展名或默认为.jpg
        # 提取文件扩展名
        extension = os.path.splitext(urllib.parse.urlparse(img_url).path)[1]
        if not extension or len(extension) > 5:  # 检查扩展名是否合法
            extension = '.jpg'
        
        img_filename = f"{img_hash}{extension}"
        img_path = os.path.join(img_folder, img_filename)
        
        # 检查文件是否已存在
        if not os.path.exists(img_path):
            # 下载图片
            response = requests.get(img_url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(img_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"下载图片: {img_url} -> {img_path}")
            else:
                print(f"无法下载图片 {img_url}, 状态码: {response.status_code}")
                return None
        
        return img_path
    except Exception as e:
        print(f"下载图片时出错 {img_url}: {str(e)}")
        return None

def process_images(soup, base_url, img_folder):
    """
    处理HTML中的所有图片，下载并替换为本地路径
    """
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # 跳过数据URI
            if src.startswith('data:'):
                continue
            
            # 下载图片
            local_path = download_image(src, base_url, img_folder)
            if local_path:
                # 使用相对路径更新src属性
                img['src'] = os.path.relpath(local_path, os.getcwd()).replace('\\', '/')
    
    return soup

def replace_md_image_urls(markdown_text, base_url, img_folder):
    """
    替换Markdown中的图片URL为本地路径
    """
    # 匹配Markdown中的图片链接: ![alt](url)
    img_pattern = r'!\[(.*?)\]\((https?://[^)]+)\)'
    
    def replace_url(match):
        alt_text = match.group(1)
        img_url = match.group(2)
        
        # 下载图片
        local_path = download_image(img_url, base_url, img_folder)
        if local_path:
            # 替换为本地路径
            rel_path = os.path.relpath(local_path, os.getcwd()).replace('\\', '/')
            return f'![{alt_text}]({rel_path})'
        return match.group(0)  # 如果下载失败，保持原样
    
    # 替换所有匹配的图片URL
    return re.sub(img_pattern, replace_url, markdown_text)

def get_site_config(url):
    """
    根据URL获取网站特定的配置
    """
    domain = urlparse(url).netloc
    for site_domain, config in SITE_CONFIGS.items():
        if site_domain in domain:
            return config
    return SITE_CONFIGS['default']

def extract_urls_from_text(text):
    """
    从文本中提取URL
    
    参数:
    - text: 输入文本
    
    返回:
    - 提取到的URL列表
    """
    # URL正则表达式模式，匹配http和https链接以及www开头的链接
    # 使用更精确的模式，只匹配到空白字符或特定分隔符为止
    url_pattern = r'(?:https?://|www\.)[^\s<>"\'，：；！？、]+'
    
    # 查找所有匹配
    raw_urls = re.findall(url_pattern, text)
    
    normalized_urls = []
    for url in raw_urls:
        # 处理www前缀
        if url.startswith('www.'):
            url = 'https://' + url
        
        # 清理URL末尾的标点符号（但保留URL本身的有效字符）
        # 移除常见的句末标点符号
        url = re.sub(r'[,.:;!?，：；！？、]+$', '', url)
        
        # 确保URL不为空且格式正确
        if url and (url.startswith('http://') or url.startswith('https://')):
            normalized_urls.append(url)
    
    return normalized_urls

def fetch_and_convert_to_markdown(url, img_folder='images', cookies=None, anchor_strategy='section', js_mode='auto', wait_selectors_override=None):
    """
    获取网页内容，下载图片，并转换为Markdown格式
    
    参数:
    - url: 网页URL
    - img_folder: 图片保存文件夹
    - cookies: 可选的cookies字典
    """
    try:
        # 创建图片文件夹
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
        
        # 获取网站特定配置
        site_config = get_site_config(url)
        
        # 准备请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        # 更新网站特定的headers
        headers.update(site_config['headers'])
        
        # 检查是否需要cookies
        if site_config['needs_cookies'] and not cookies:
            print(f"警告: 该网站({urlparse(url).netloc})可能需要cookies才能正常访问")
        
        # JS 渲染策略
        site_conf = get_site_config(url)
        wait_selectors = site_conf.get('wait_selectors') if isinstance(site_conf, dict) else None
        if wait_selectors_override:
            wait_selectors = wait_selectors_override
    
        if js_mode == 'on':
            use_js = True
        elif js_mode == 'off':
            use_js = False
        else:
            # 如果配置明确要求JS，直接标记为True
            if site_conf and site_conf.get('needs_js'):
                use_js = True
            else:
                # 否则暂时设为False，稍后根据内容判断
                use_js = False

        soup = None
        response_text = None

        # 如果不需要强制JS，或者需要先获取内容来判断是否需要JS
        if not use_js:
            try:
                # 发送请求获取网页内容（初次尝试）
                response = requests.get(url, headers=headers, cookies=cookies, timeout=20)
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                response_text = response.text
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 再次检查是否需要JS（基于内容）
                if js_mode == 'auto' and should_render_with_js(url, soup, response_text):
                    use_js = True
            except Exception as e:
                print(f"Requests请求失败，尝试使用Playwright: {e}")
                use_js = True

        if use_js:
            print("使用Playwright渲染页面...")
            rendered_html = render_page_with_playwright(url, headers=headers, cookies=cookies, wait_selectors=wait_selectors)
            if rendered_html:
                soup = BeautifulSoup(rendered_html, 'html.parser')
            else:
                if soup is None:
                    raise Exception("无法获取网页内容 (Playwright和Requests均失败)")
    
        if not soup:
             raise Exception("无法解析网页内容")

        # 提取网页标题
        title = soup.title.string if soup.title else 'Untitled Page'
        if title is None:
            title = 'Untitled Page'
        
        # 处理图片：下载并替换URL
        soup = process_images(soup, url, img_folder)
        
        # 移除不必要的元素
        for element in soup.select('script, style, iframe, nav, footer, .sidebar, .advertisement, .ads'):
            element.decompose()
        
        # 提取主要内容
        main_content = None
        
        # 首先尝试使用网站特定的选择器
        for selector in site_config['main_content_selectors']:
            content = soup.select_one(selector)
            if content:
                main_content = content
                break

        # 如果没有找到主要内容区域，则使用body
        if not main_content:
            main_content = soup.find('body')
            if not main_content:
                main_content = soup

        # 处理URL中的锚点（fragment），例如 #single-file-parsing
        # 对于文档站点（如 ragas.org.cn），默认使用完整页面模式
        domain = urlparse(url).netloc
        is_doc_site = 'ragas.org.cn' in domain or 'docs.' in domain
        if is_doc_site and anchor_strategy == 'section':
            anchor_strategy = 'full'
        
        fragment = urlparse(url).fragment
        if fragment and anchor_strategy != 'full':
            anchor_el = soup.find(id=fragment)
            if not anchor_el:
                # 有些站点将 fragment 存在 name 或 data-id 上
                anchor_el = soup.find(attrs={'name': fragment}) or soup.find(attrs={'data-id': fragment})
            if anchor_el:
                title_el = anchor_el
                # 如果锚点在标题内部，如 <a id="..."> 放在 <h2>内
                if anchor_el.name == 'a' and anchor_el.parent and anchor_el.parent.name in ['h1','h2','h3','h4','h5','h6']:
                    title_el = anchor_el.parent
                heading_level = 1
                if title_el.name and title_el.name.startswith('h') and title_el.name[1:].isdigit():
                    heading_level = int(title_el.name[1:])
                # 收集后续兄弟节点，直到遇到同级或更高的标题
                siblings_to_move = []
                for sib in title_el.next_siblings:
                    if getattr(sib, 'name', None) in ['h1','h2','h3','h4','h5','h6']:
                        sib_level = int(sib.name[1:]) if sib.name and sib.name[1:].isdigit() else 7
                        if sib_level <= heading_level:
                            break
                    siblings_to_move.append(sib)
                section_container = soup.new_tag('div')
                section_container.append(title_el)
                for sib in siblings_to_move:
                    section_container.append(sib)
                main_content = section_container
        
        # 将内容转换为Markdown格式
        markdown_content = markdownify.markdownify(str(main_content), heading_style="ATX")
        
        # 替换Markdown文本中的图片URL
        markdown_content = replace_md_image_urls(markdown_content, url, img_folder)
        
        # 生成完整的Markdown文档
        markdown_document = f"# {title}\n\n原文链接: {url}\n\n{markdown_content}"
        
        return markdown_document, title
    
    except Exception as e:
        print(f"处理网页时出错: {str(e)}")
        return None, "Error_Page"

def convert_html_to_markdown(html, url, img_folder='images'):
    try:
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else 'Untitled Page'
        if title is None:
            title = 'Untitled Page'
        soup = process_images(soup, url, img_folder)
        for element in soup.select('script, style, iframe, nav, footer, .sidebar, .advertisement, .ads'):
            element.decompose()
        site_config = get_site_config(url)
        main_content = None
        for selector in site_config['main_content_selectors']:
            content = soup.select_one(selector)
            if content:
                main_content = content
                break
        if not main_content:
            main_content = soup.find('body')
            if not main_content:
                main_content = soup
        markdown_content = markdownify.markdownify(str(main_content), heading_style="ATX")
        markdown_content = replace_md_image_urls(markdown_content, url, img_folder)
        markdown_document = f"# {title}\n\n原文链接: {url}\n\n{markdown_content}"
        return markdown_document, title
    except Exception as e:
        print(f"处理HTML时出错: {str(e)}")
        return None, "Error_Page"

def render_with_actions(url, actions, headers=None, cookies=None, headless=False, channel="chrome", timeout_ms=15000):
    if sync_playwright is None:
        return None
    try:
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(headless=headless, channel=channel)
            except Exception:
                browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            if headers:
                context.set_extra_http_headers(headers)
            if cookies:
                with contextlib.suppress(Exception):
                    context.add_cookies(cookies)
            page = context.new_page()
            page.goto(url, wait_until='networkidle')
            for act in actions or []:
                t = (act or {}).get('type')
                if t == 'goto':
                    u = act.get('url') or url
                    wu = act.get('waitUntil') or 'networkidle'
                    with contextlib.suppress(Exception):
                        page.goto(u, wait_until=wu)
                elif t == 'wait':
                    sels = act.get('selectors') or []
                    to = act.get('timeoutMs') or timeout_ms
                    for sel in sels:
                        with contextlib.suppress(Exception):
                            page.wait_for_selector(sel, timeout=to)
                            break
                elif t == 'click':
                    sel = act.get('selector')
                    if sel:
                        with contextlib.suppress(Exception):
                            page.click(sel)
                elif t == 'type':
                    sel = act.get('selector')
                    txt = act.get('text') or ''
                    delay = act.get('delayMs') or 0
                    submit = bool(act.get('submit'))
                    if sel:
                        with contextlib.suppress(Exception):
                            page.fill(sel, '')
                            page.type(sel, txt, delay=delay)
                            if submit:
                                page.keyboard.press('Enter')
                elif t == 'scroll':
                    dest = act.get('to')
                    val = act.get('value')
                    if dest == 'top':
                        page.evaluate('window.scrollTo(0, 0)')
                    elif dest == 'bottom':
                        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    elif dest == 'y' and isinstance(val, int):
                        page.evaluate(f'window.scrollTo(0, {val})')
                elif t == 'sleep':
                    ms = act.get('ms') or 0
                    if ms > 0:
                        page.wait_for_timeout(ms)
                elif t == 'screenshot':
                    path = act.get('path')
                    full = bool(act.get('fullPage')) if act.get('fullPage') is not None else True
                    with contextlib.suppress(Exception):
                        if path:
                            page.screenshot(path=path, full_page=full)
                        else:
                            page.screenshot(full_page=full)
                elif t == 'evaluate':
                    script = act.get('script') or ''
                    if script:
                        with contextlib.suppress(Exception):
                            page.evaluate(script)
            content = page.content()
            context.close()
            browser.close()
            return content
    except Exception as e:
        print(f"Playwright 交互失败: {e}")
        return None

async def _async_render_with_actions(url, actions, headers=None, cookies=None, headless=False, channel="chrome", timeout_ms=15000):
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return None
    try:
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(
                    headless=headless, 
                    channel=channel,
                    args=['--disable-blink-features=AutomationControlled']
                )
            except Exception:
                browser = await p.chromium.launch(
                    headless=headless,
                    args=['--disable-blink-features=AutomationControlled']
                )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 注入反检测脚本
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            if headers:
                await context.set_extra_http_headers(headers)
            if cookies:
                with contextlib.suppress(Exception):
                    await context.add_cookies(cookies)
            page = await context.new_page()
            await page.goto(url, wait_until='networkidle')
            for act in actions or []:
                t = (act or {}).get('type')
                if t == 'goto':
                    u = act.get('url') or url
                    wu = act.get('waitUntil') or 'networkidle'
                    with contextlib.suppress(Exception):
                        await page.goto(u, wait_until=wu)
                elif t == 'wait':
                    sels = act.get('selectors') or []
                    to = act.get('timeoutMs') or timeout_ms
                    for sel in sels:
                        with contextlib.suppress(Exception):
                            await page.wait_for_selector(sel, timeout=to)
                            break
                elif t == 'click':
                    sel = act.get('selector')
                    if sel:
                        with contextlib.suppress(Exception):
                            await page.click(sel)
                elif t == 'type':
                    sel = act.get('selector')
                    txt = act.get('text') or ''
                    delay = act.get('delayMs') or 0
                    submit = bool(act.get('submit'))
                    if sel:
                        with contextlib.suppress(Exception):
                            await page.fill(sel, '')
                            if delay:
                                await page.type(sel, txt, delay=delay)
                            else:
                                await page.type(sel, txt)
                            if submit:
                                await page.keyboard.press('Enter')
                elif t == 'scroll':
                    dest = act.get('to')
                    val = act.get('value')
                    if dest == 'top':
                        await page.evaluate('window.scrollTo(0, 0)')
                    elif dest == 'bottom':
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    elif dest == 'y' and isinstance(val, int):
                        await page.evaluate(f'window.scrollTo(0, {val})')
                elif t == 'sleep':
                    ms = act.get('ms') or 0
                    if ms > 0:
                        await page.wait_for_timeout(ms)
                elif t == 'screenshot':
                    path = act.get('path')
                    full = bool(act.get('fullPage')) if act.get('fullPage') is not None else True
                    with contextlib.suppress(Exception):
                        if path:
                            await page.screenshot(path=path, full_page=full)
                        else:
                            await page.screenshot(full_page=full)
                elif t == 'evaluate':
                    script = act.get('script') or ''
                    if script:
                        with contextlib.suppress(Exception):
                            await page.evaluate(script)
            content = await page.content()
            await context.close()
            await browser.close()
            return content
    except Exception as e:
        print(f"Playwright 异步交互失败: {e}")
        return None

def render_with_actions_threaded(url, actions, headers=None, cookies=None, headless=False, channel="chrome", timeout_ms=15000):
    q = queue.Queue()
    def worker():
        try:
            import asyncio as _asyncio
            result = _asyncio.run(_async_render_with_actions(url, actions, headers, cookies, headless, channel, timeout_ms))
            q.put(result)
        except Exception as e:
            q.put(None)
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join()
    try:
        return q.get_nowait()
    except Exception:
        return None

def process_url_text_mode(text, img_folder='images', cookies=None):
    """
    从文本中提取URL并爬取每个URL，然后合并结果到一个Markdown文件
    
    参数:
    - text: 包含URL的文本
    - img_folder: 图片保存文件夹
    - cookies: 可选的cookies字典
    
    返回:
    - 合并后的Markdown文档
    - 爬取结果摘要
    """
    # 提取URL
    urls = extract_urls_from_text(text)
    
    if not urls:
        print("未在提供的文本中找到任何URL")
        return None, "未找到URL"
    
    print(f"从文本中提取到 {len(urls)} 个URL:")
    for i, url in enumerate(urls):
        print(f"{i+1}. {url}")
    
    # 爬取结果
    results = []
    successful_urls = []
    failed_urls = []
    
    # 爬取每个URL
    for i, url in enumerate(urls):
        print(f"\n开始爬取 URL {i+1}/{len(urls)}: {url}")
        
        start_time = time.time()
        markdown_output, page_title = fetch_and_convert_to_markdown(url, img_folder, cookies)
        end_time = time.time()
        
        if markdown_output:
            results.append(markdown_output)
            successful_urls.append(url)
            print(f"成功爬取 {url}, 耗时: {end_time - start_time:.2f} 秒")
        else:
            failed_urls.append(url)
            print(f"爬取失败: {url}")
    
    # 如果没有成功爬取任何URL，返回None
    if not results:
        return None, "所有URL爬取失败"
    
    # 合并结果
    merged_content = "\n\n---\n\n".join(results)
    
    # 添加批量爬取摘要信息
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    summary = f"# 批量爬取结果\n\n爬取时间: {timestamp}\n\n"
    summary += f"## 爬取摘要\n\n- 总计URL: {len(urls)}\n- 成功: {len(successful_urls)}\n- 失败: {len(failed_urls)}\n\n"
    
    if failed_urls:
        summary += "## 爬取失败的URL\n\n"
        for i, url in enumerate(failed_urls):
            summary += f"{i+1}. {url}\n"
        summary += "\n"
    
    # 最终文档
    final_document = f"{summary}\n\n---\n\n{merged_content}"
    
    # 爬取结果摘要
    result_summary = f"批量爬取完成: 共 {len(urls)} 个URL，成功 {len(successful_urls)} 个，失败 {len(failed_urls)} 个"
    
    return final_document, result_summary

# 使用示例
if __name__ == "__main__":
    # CLI 快捷模式：支持直接通过命令行参数抓取并退出
    try:
        _parser = argparse.ArgumentParser(add_help=False)
        _parser.add_argument("--url", "-u")
        _parser.add_argument("--out", "-o")
        _parser.add_argument("--anchor", choices=["section","full"], default="section")
        _parser.add_argument("--js", choices=["auto","on","off"], default="auto")
        _parser.add_argument("--wait", nargs="*")
        _known, _ = _parser.parse_known_args()
        if _known.url:
            md, title = fetch_and_convert_to_markdown(
                _known.url,
                anchor_strategy=("full" if _known.anchor == "full" else "section"),
                js_mode=_known.js,
                wait_selectors_override=_known.wait,
            )
            if md:
                # 使用标题生成默认文件名
                default_name = f"{sanitize_filename(title)}_{time.strftime('%Y%m%d_%H%M%S')}.md"
                out_path = _known.out or default_name
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(md)
                print(f"内容已成功爬取并保存为 {out_path}")
                raise SystemExit(0)
            else:
                print("爬取失败，请检查网址或稍后重试")
                raise SystemExit(2)
    except Exception:
        # 保持与原交互模式兼容；如未传入参数或解析失败，继续原流程
        pass

    try:
        print("BasicWebCrawler - 网页爬虫工具")
        print("=" * 50)
        print("1. 直接爬取单个URL")
        print("2. 从文本中提取URL并批量爬取")
        print("=" * 50)
        
        choice = input("请选择运行模式 (1/2): ").strip()
        
        if choice == "1":
            # 单个URL模式
            url = input("请输入网址: ")
            print(f"开始爬取 {url} 的内容...")
            
            # 检查是否需要cookies
            site_config = get_site_config(url)
            cookies = None
            if site_config['needs_cookies']:
                cookies_input = input("该网站可能需要cookies，请输入cookies文件路径（直接回车跳过）: ")
                if cookies_input.strip():
                    try:
                        with open(cookies_input, 'r') as f:
                            cookies = json.load(f)
                    except Exception as e:
                        print(f"读取cookies文件失败: {str(e)}")
                        print("将继续尝试不使用cookies进行爬取...")
            
            start_time = time.time()
            markdown_output, page_title = fetch_and_convert_to_markdown(url, cookies=cookies)
            end_time = time.time()
            
            if markdown_output:
                # 使用网页标题作为文件名
                sanitized_title = sanitize_filename(page_title)
                if not sanitized_title:
                    sanitized_title = "untitled_page"
                
                # 添加时间戳以避免文件名冲突
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = f"{sanitized_title}_{timestamp}.md"
                
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(markdown_output)
                    
                    print(f"内容已成功爬取并保存为 {output_file}")
                    print(f"处理完成，耗时: {end_time - start_time:.2f} 秒")
                    print(f"图片已保存在 './images/' 目录下")
                except OSError as e:
                    print(f"创建文件时出错: {str(e)}")
                    fallback_filename = f"webpage_{timestamp}.md"
                    with open(fallback_filename, 'w', encoding='utf-8') as f:
                        f.write(markdown_output)
                    print(f"已使用备用文件名保存内容: {fallback_filename}")
            else:
                print("爬取失败，请检查网址是否正确")
        
        elif choice == "2":
            # 批量URL模式
            print("请输入包含URL的文本:")
            print("(每行输入完成后按回车，输入完所有内容后按Ctrl+Z然后回车结束输入)")
            print("(Windows系统也可按Ctrl+D结束输入)")
            print("=" * 50)
            text_lines = []
            
            try:
                line_num = 1
                while True:
                    try:
                        line = input(f"第{line_num}行> ")
                        text_lines.append(line)
                        line_num += 1
                        # 打印提示，表示已接收到输入
                        if line.strip():
                            print(f"已添加输入: {line}")
                    except EOFError:
                        # 捕获EOF
                        print("\n输入结束，开始处理...")
                        break
            except KeyboardInterrupt:
                # 捕获键盘中断
                print("\n输入被中断")
                if not text_lines:
                    print("未输入任何文本，退出程序")
                    exit(0)
                print("将处理已输入的内容...")
            
            text = "\n".join(text_lines)
            
            if not text.strip():
                print("未输入任何文本，退出程序")
                exit(0)
            
            print("\n开始从文本中提取URL并爬取内容...")
            
            # 询问是否需要使用cookies
            cookies = None
            cookies_input = input("如果需要cookies，请输入cookies文件路径（直接回车跳过）: ")
            if cookies_input.strip():
                try:
                    with open(cookies_input, 'r') as f:
                        cookies = json.load(f)
                except Exception as e:
                    print(f"读取cookies文件失败: {str(e)}")
                    print("将继续尝试不使用cookies进行爬取...")
            
            start_time = time.time()
            markdown_output, result_summary = process_url_text_mode(text, cookies=cookies)
            end_time = time.time()
            
            if markdown_output:
                # 创建输出文件名
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = f"批量爬取结果_{timestamp}.md"
                
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(markdown_output)
                    
                    print(f"\n{result_summary}")
                    print(f"内容已成功保存为 {output_file}")
                    print(f"处理完成，总耗时: {end_time - start_time:.2f} 秒")
                    print(f"图片已保存在 './images/' 目录下")
                except OSError as e:
                    print(f"创建文件时出错: {str(e)}")
                    fallback_filename = f"批量爬取_{timestamp}.md"
                    with open(fallback_filename, 'w', encoding='utf-8') as f:
                        f.write(markdown_output)
                    print(f"已使用备用文件名保存内容: {fallback_filename}")
            else:
                print("\n爬取失败，未能成功处理任何URL")
        
        else:
            print("无效的选择，请选择1或2")
    
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
