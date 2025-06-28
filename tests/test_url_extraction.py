import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler import extract_urls_from_text, process_url_text_mode

class TestUrlExtraction(unittest.TestCase):
    """测试URL提取功能"""

    def test_extract_urls_from_text(self):
        """测试从文本中提取URL的功能"""
        # 测试文本
        test_text = """
        使用教程• https://www.bilibili.com/video/BV1rWwWeaEX1/：哔哩哔哩上的 Flowith 2.0 官方教程视频，
        帮助用户快速上手使用该工具。替代品参考• https://www.aibase.com/zh/tool/35735：列举了一些 
        Flowith 2.0 的替代品，用户可以参考对比其功能和特点，以便更好地选择适合自己的工具。
        还有一些其他网站 www.example.com
        """
        
        # 提取URL
        urls = extract_urls_from_text(test_text)
        
        # 验证结果
        expected_urls = [
            'https://www.bilibili.com/video/BV1rWwWeaEX1/',
            'https://www.aibase.com/zh/tool/35735',
            'https://www.example.com'
        ]
        
        self.assertEqual(len(urls), 3, "应该提取到3个URL")
        for url in expected_urls:
            self.assertIn(url, urls, f"未能提取到URL: {url}")
    
    def test_url_normalization(self):
        """测试URL规范化功能"""
        # 测试带www前缀的URL
        test_text = "访问 www.example.com 查看更多信息"
        urls = extract_urls_from_text(test_text)
        
        self.assertEqual(len(urls), 1, "应该提取到1个URL")
        self.assertEqual(urls[0], "https://www.example.com", "应该将www前缀转换为https://")
    
    def test_url_cleaning(self):
        """测试URL清理功能"""
        # 测试带标点符号的URL
        test_text = "访问 https://example.com/page?id=123, 查看更多信息"
        urls = extract_urls_from_text(test_text)
        
        self.assertEqual(len(urls), 1, "应该提取到1个URL")
        self.assertEqual(urls[0], "https://example.com/page?id=123", "应该移除URL末尾的标点符号")
    
    @patch('crawler.fetch_and_convert_to_markdown')
    def test_process_url_text_mode(self, mock_fetch):
        """测试批量处理URL的功能"""
        # 模拟fetch_and_convert_to_markdown的行为
        mock_fetch.side_effect = [
            ("# 测试页面1\n\n内容1", "测试页面1"),  # 第一个URL成功
            (None, "Error_Page"),                  # 第二个URL失败
            ("# 测试页面3\n\n内容3", "测试页面3")   # 第三个URL成功
        ]
        
        # 测试文本
        test_text = """
        https://www.example.com/page1
        https://www.example.com/page2
        https://www.example.com/page3
        """
        
        # 调用函数
        result, summary = process_url_text_mode(test_text)
        
        # 验证函数调用
        self.assertEqual(mock_fetch.call_count, 3, "应该调用3次fetch_and_convert_to_markdown")
        
        # 验证结果
        self.assertIn("# 批量爬取结果", result, "结果应包含批量爬取标题")
        self.assertIn("总计URL: 3", result, "结果应包含URL总数")
        self.assertIn("成功: 2", result, "结果应包含成功数量")
        self.assertIn("失败: 1", result, "结果应包含失败数量")
        self.assertIn("# 测试页面1", result, "结果应包含第一个页面的内容")
        self.assertIn("# 测试页面3", result, "结果应包含第三个页面的内容")
        self.assertIn("批量爬取完成", summary, "摘要应包含完成信息")

if __name__ == '__main__':
    unittest.main() 