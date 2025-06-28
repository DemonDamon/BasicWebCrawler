#!/usr/bin/env python3
"""
调试MCP服务器
"""

import asyncio
import sys
from pathlib import Path

# 添加当前目录到Python路径，以便导入mcp_server模块
sys.path.append(str(Path(__file__).parent))

from fastmcp import Client
from mcp_server import mcp

async def debug_mcp():
    """调试MCP服务器"""
    
    client = Client(mcp)
    
    async with client:
        print("🔗 连接成功")
        
        # 测试简单的工具调用
        try:
            print("\n🔍 测试extract_urls工具...")
            result = await client.call_tool("extract_urls", {"text": "https://www.example.com"})
            print(f"结果类型: {type(result)}")
            print(f"结果内容: {result}")
            
            # 尝试不同的访问方式
            if hasattr(result, '__dict__'):
                print(f"结果属性: {result.__dict__}")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_mcp()) 