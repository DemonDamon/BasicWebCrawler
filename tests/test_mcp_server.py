#!/usr/bin/env python3
"""
测试BasicWebCrawler MCP服务器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录和mcp_server目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "mcp_server"))

from fastmcp import Client
from mcp_server import mcp

async def test_mcp_server():
    """测试MCP服务器的各种功能"""
    
    # 创建客户端连接到我们的MCP服务器
    client = Client(mcp)
    
    async with client:
        print("🔗 已连接到BasicWebCrawler MCP服务器")
        
        # 测试ping连接
        try:
            await client.ping()
            print("✅ 服务器连接正常")
        except Exception as e:
            print(f"❌ 服务器连接失败: {e}")
            return
        
        # 获取可用工具列表
        print("\n📋 获取可用工具...")
        tools = await client.list_tools()
        print(f"可用工具数量: {len(tools)}")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
        
        # 获取可用资源列表
        print("\n📋 获取可用资源...")
        resources = await client.list_resources()
        print(f"可用资源数量: {len(resources)}")
        for resource in resources:
            print(f"  • {resource.uri}: {resource.description}")
        
        # 获取可用提示列表
        print("\n📋 获取可用提示...")
        prompts = await client.list_prompts()
        print(f"可用提示数量: {len(prompts)}")
        for prompt in prompts:
            print(f"  • {prompt.name}: {prompt.description}")
        
        # 测试URL提取功能
        print("\n🔍 测试URL提取功能...")
        test_text = """
        这里有一些网站链接：
        https://www.example.com
        https://github.com/microsoft/vscode
        www.google.com
        还有一个B站视频：https://www.bilibili.com/video/BV1234567890
        """
        
        try:
            result = await client.call_tool("extract_urls", {"text": test_text})
            print("URL提取结果:")
            if isinstance(result, list) and len(result) > 0:
                print(result[0].text)
            else:
                print(str(result))
        except Exception as e:
            print(f"❌ URL提取测试失败: {e}")
        
        # 测试网站配置检查
        print("\n🌐 测试网站配置检查...")
        try:
            result = await client.call_tool("check_site_config", {"url": "https://www.zhihu.com/question/123456"})
            print("知乎网站配置:")
            if isinstance(result, list) and len(result) > 0:
                print(result[0].text)
            else:
                print(str(result))
        except Exception as e:
            print(f"❌ 网站配置检查失败: {e}")
        
        # 测试支持的网站列表
        print("\n📝 测试支持的网站列表...")
        try:
            result = await client.call_tool("get_supported_sites", {})
            print("支持的网站:")
            if isinstance(result, list) and len(result) > 0:
                print(result[0].text)
            else:
                print(str(result))
        except Exception as e:
            print(f"❌ 获取支持网站列表失败: {e}")
        
        # 测试资源访问
        print("\n📊 测试配置资源访问...")
        try:
            result = await client.read_resource("crawler://config")
            print("爬虫配置信息:")
            if isinstance(result, list) and len(result) > 0:
                print(result[0].text)
            else:
                print(str(result))
        except Exception as e:
            print(f"❌ 读取配置资源失败: {e}")
        
        # 测试提示模板
        print("\n💬 测试提示模板...")
        try:
            result = await client.get_prompt("crawl_webpage_prompt", {
                "url": "https://www.example.com",
                "use_cookies": False
            })
            print("爬取网页提示:")
            if hasattr(result, 'messages') and len(result.messages) > 0:
                print(result.messages[0].content)
            elif isinstance(result, str):
                print(result)
            else:
                print(str(result))
        except Exception as e:
            print(f"❌ 获取提示模板失败: {e}")
        
        print("\n✅ MCP服务器测试完成！")

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 