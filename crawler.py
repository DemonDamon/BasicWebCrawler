import requests
from bs4 import BeautifulSoup
import markdownify
import os
import urllib.parse
import re
from urllib.parse import urljoin, urlparse
import hashlib
import time
import json
import tempfile
try:
    import browser_cookie3
except ImportError:
    browser_cookie3 = None

# 不需要下载的图片格式
IGNORED_EXTENSIONS = ['.ico', '.webp', '.svg', '.gif', '.bmp', '.tiff']

# 网站特定配置
SITE_CONFIGS = {
    'zhihu.com': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.zhihu.com',
            'sec-ch-ua': '"Google Chrome";v="91", "Chromium";v="91"',
        },
        'main_content_selectors': ['div.Post-RichText', 'div.RichText', 'div.Post-content'],
        'needs_cookies': True
    },
    'default': {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        },
        'main_content_selectors': ['article', 'main', '.main-content', '.post-content', '.entry-content', '.content', '#content'],
        'needs_cookies': False
    }
}

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

def fetch_and_convert_to_markdown(url, img_folder='images', cookies=None):
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        # 更新网站特定的headers
        headers.update(site_config['headers'])
        
        # 检查是否需要cookies
        if site_config['needs_cookies'] and not cookies:
            print(f"警告: 该网站({urlparse(url).netloc})可能需要cookies才能正常访问")
        
        # 发送请求获取网页内容
        response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        
        # 检查请求是否成功
        if response.status_code != 200:
            print(f"Error fetching {url}: {response.status_code}")
            return None, None
        
        # 解析网页内容
        soup = BeautifulSoup(response.content, 'html.parser')
        
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

# 使用示例
if __name__ == "__main__":
    try:
        url = input("请输入网址: ")
        print(f"开始爬取 {url} 的内容...")
        
        # 检查是否需要cookies
        site_config = get_site_config(url)
        cookies = None
        cookies_path = None
        
        if site_config['needs_cookies']:
            auto_cookie = input("该网站可能需要cookies，是否自动从浏览器获取？(y/n): ").strip().lower()
            
            if auto_cookie == 'y' and browser_cookie3:
                try:
                    # 从URL获取域名
                    domain = urlparse(url).netloc
                    print(f"正在从浏览器获取 {domain} 的cookies...")
                    
                    # 从Chrome浏览器获取指定网站的cookies
                    browser_cookies = browser_cookie3.chrome(domain_name=domain)
                    
                    # 将cookies转换为字典
                    cookies_dict = {cookie.name: cookie.value for cookie in browser_cookies}
                    
                    if cookies_dict:
                        # 创建临时文件保存cookies
                        fd, cookies_path = tempfile.mkstemp(suffix='.json', prefix='cookies_')
                        with os.fdopen(fd, 'w') as f:
                            json.dump(cookies_dict, f)
                        
                        print(f"成功获取cookies并保存到临时文件: {cookies_path}")
                        cookies = cookies_dict
                    else:
                        print(f"未找到 {domain} 的cookies，请确保您已在浏览器中登录该网站")
                        
                except Exception as e:
                    print(f"自动获取cookies失败: {str(e)}")
                    print("将尝试手动输入cookies文件...")
            
            # 如果自动获取失败或用户选择手动提供
            if not cookies:
                cookies_input = input("请输入cookies文件路径（直接回车跳过）: ")
                if cookies_input.strip():
                    try:
                        cookies_path = cookies_input
                        with open(cookies_input, 'r') as f:
                            cookies = json.load(f)
                    except Exception as e:
                        print(f"读取cookies文件失败: {str(e)}")
                        print("将继续尝试不使用cookies进行爬取...")
        
        start_time = time.time()
        markdown_output, page_title = fetch_and_convert_to_markdown(url, cookies=cookies)
        end_time = time.time()
        
        # 清理临时文件
        if cookies_path and cookies_path.startswith(tempfile.gettempdir()):
            try:
                os.remove(cookies_path)
                print(f"临时cookies文件已删除: {cookies_path}")
            except:
                pass
        
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
    
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
