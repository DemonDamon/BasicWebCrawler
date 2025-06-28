import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler import get_site_config, SITE_CONFIGS

class TestSiteConfigs(unittest.TestCase):
    """测试网站特定配置功能"""

    def test_zhihu_config(self):
        """测试知乎网站配置"""
        url = "https://www.zhihu.com/question/12345"
        config = get_site_config(url)
        
        self.assertEqual(config['needs_cookies'], True, "知乎应该需要cookies")
        self.assertIn('div.Post-RichText', config['main_content_selectors'], "知乎应该包含特定的内容选择器")
        self.assertEqual(config['headers']['Referer'], 'https://www.zhihu.com', "知乎应该有特定的Referer")

    def test_bilibili_config(self):
        """测试B站网站配置"""
        url = "https://www.bilibili.com/video/BV1rWwWeaEX1"
        config = get_site_config(url)
        
        self.assertEqual(config['needs_cookies'], False, "B站不应该强制需要cookies")
        self.assertIn('.video-info-container', config['main_content_selectors'], "B站应该包含视频信息容器选择器")
        self.assertEqual(config['headers']['Referer'], 'https://www.bilibili.com', "B站应该有特定的Referer")

    def test_aibase_config(self):
        """测试AI Base网站配置"""
        url = "https://www.aibase.com/zh/tool/35735"
        config = get_site_config(url)
        
        self.assertEqual(config['needs_cookies'], False, "AI Base不应该强制需要cookies")
        self.assertIn('.tool-container', config['main_content_selectors'], "AI Base应该包含工具容器选择器")
        self.assertEqual(config['headers']['Referer'], 'https://www.aibase.com', "AI Base应该有特定的Referer")

    def test_default_config(self):
        """测试默认网站配置"""
        url = "https://www.example.com/page"
        config = get_site_config(url)
        
        self.assertEqual(config, SITE_CONFIGS['default'], "未知网站应该使用默认配置")
        self.assertEqual(config['needs_cookies'], False, "默认配置不应该需要cookies")
        self.assertIn('article', config['main_content_selectors'], "默认配置应该包含通用内容选择器")

    def test_subdomain_config(self):
        """测试子域名配置匹配"""
        url = "https://zhuanlan.zhihu.com/p/12345"
        config = get_site_config(url)
        
        # 应该匹配到zhihu.com的配置
        self.assertEqual(config['headers']['Referer'], 'https://www.zhihu.com', "子域名应该匹配到主域名配置")

if __name__ == '__main__':
    unittest.main() 