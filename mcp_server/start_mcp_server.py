#!/usr/bin/env python3
"""
BasicWebCrawler MCP服务器统一启动脚本

集成依赖检查、配置示例显示、多传输方式支持的完整启动器
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def check_dependencies():
    """检查必要的依赖是否已安装"""
    # 包名映射：pip包名 -> 导入模块名
    package_mappings = {
        'fastmcp': 'fastmcp',
        'requests': 'requests', 
        'beautifulsoup4': 'bs4',
        'markdownify': 'markdownify'
    }
    
    missing_packages = []
    
    for pip_name, import_name in package_mappings.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装依赖:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def show_config_examples(transport, host, port, path):
    """显示AI助手配置示例"""
    project_root = str(Path(__file__).parent.parent).replace("\\", "/")
    mcp_server_path = str(Path(__file__).parent / "mcp_server.py").replace("\\", "/")
    
    print("\n🤖 AI助手配置示例:")
    print("=" * 40)
    
    if transport == "stdio":
        print("📋 STDIO 传输配置:")
        print("Claude Desktop / Cursor 配置:")
        config = f'''{{
  "mcpServers": {{
    "basic-web-crawler": {{
      "command": "python",
      "args": ["{mcp_server_path}"],
      "cwd": "{project_root}"
    }}
  }}
}}'''
        print(config)
    
    elif transport == "sse":
        print(f"🌐 SSE 传输配置:")
        print(f"服务器地址: http://{host}:{port}/sse")
        print("Claude Desktop / Cursor 配置:")
        config = f'''{{
  "mcpServers": {{
    "basic-web-crawler": {{
      "type": "sse",
      "url": "http://{host}:{port}/sse"
    }}
  }}
}}'''
        print(config)
        
        print("\n或使用 mcp-proxy 转换为 STDIO:")
        proxy_config = f'''{{
  "mcpServers": {{
    "basic-web-crawler": {{
      "command": "mcp-proxy",
      "args": ["http://{host}:{port}/sse"]
    }}
  }}
}}'''
        print(proxy_config)
    
    elif transport == "http":
        print(f"⚡ HTTP 传输配置:")
        print(f"服务器地址: http://{host}:{port}{path}")
        print("Claude Desktop / Cursor 配置:")
        config = f'''{{
  "mcpServers": {{
    "basic-web-crawler": {{
      "type": "streamableHttp",
      "url": "http://{host}:{port}{path}"
    }}
  }}
}}'''
        print(config)

def start_server_directly(transport, host, port, path):
    """直接启动MCP服务器（导入方式）"""
    try:
        # 添加父目录到Python路径
        sys.path.append(str(Path(__file__).parent.parent))
        
        # 导入MCP服务器
        from mcp_server import mcp
        
        print(f"\n🎯 启动MCP服务器...")
        print("提示: 按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        if transport == "stdio":
            mcp.run(transport="stdio")
        elif transport == "sse":
            mcp.run(transport="sse", host=host, port=port)
        elif transport == "http":
            mcp.run(transport="http", host=host, port=port, path=path)
            
    except ImportError as e:
        print(f"❌ 导入MCP服务器失败: {e}")
        print("尝试使用subprocess方式启动...")
        return False
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True

def start_server_subprocess():
    """使用subprocess启动MCP服务器（兼容方式）"""
    project_root = str(Path(__file__).parent.parent)
    mcp_server_file = Path(__file__).parent / "mcp_server.py"
    
    try:
        os.chdir(project_root)
        subprocess.run([sys.executable, str(mcp_server_file)], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ MCP服务器启动失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="BasicWebCrawler MCP服务器统一启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                                    # 交互式启动（STDIO）
  %(prog)s --transport stdio --auto           # 自动启动STDIO服务器
  %(prog)s --transport sse --port 8000 --auto # 自动启动SSE服务器
  %(prog)s --transport http --host 0.0.0.0 --auto # 自动启动HTTP服务器
        """
    )
    
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse", "http"], 
        default="stdio",
        help="选择传输方式 (默认: stdio)"
    )
    parser.add_argument(
        "--host", 
        default="127.0.0.1",
        help="服务器主机地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="服务器端口 (默认: 8000)"
    )
    parser.add_argument(
        "--path", 
        default="/mcp",
        help="HTTP传输的路径 (默认: /mcp)"
    )
    parser.add_argument(
        "--auto", 
        action="store_true",
        help="自动启动服务器，跳过交互式确认"
    )
    parser.add_argument(
        "--skip-deps", 
        action="store_true",
        help="跳过依赖检查"
    )
    
    args = parser.parse_args()
    
    print("🚀 BasicWebCrawler MCP服务器统一启动器")
    print("=" * 50)
    print(f"📡 传输方式: {args.transport.upper()}")
    
    # 检查依赖
    if not args.skip_deps:
        print("\n📦 检查依赖包...")
        if not check_dependencies():
            sys.exit(1)
        print("✅ 所有依赖包已安装")
    
    # 检查MCP服务器文件
    mcp_server_file = Path(__file__).parent / "mcp_server.py"
    if not mcp_server_file.exists():
        print("❌ 找不到 mcp_server.py 文件")
        sys.exit(1)
    
    # 显示配置信息
    print(f"\n🔧 配置信息:")
    print(f"   工作目录: {Path.cwd()}")
    print(f"   Python版本: {sys.version.split()[0]}")
    print(f"   MCP服务器文件: {mcp_server_file}")
    
    # 显示配置示例
    show_config_examples(args.transport, args.host, args.port, args.path)
    
    # 启动确认
    if not args.auto:
        print("\n" + "=" * 50)
        choice = input("是否现在启动MCP服务器? (y/n): ").strip().lower()
        if choice not in ['y', 'yes', '是']:
            print("\n📝 手动启动命令:")
            if args.transport == "stdio":
                print(f"python {mcp_server_file}")
            else:
                print(f"python {__file__} --transport {args.transport} --host {args.host} --port {args.port} --auto")
            return
    
    # 启动服务器
    try:
        if args.transport == "stdio":
            # STDIO模式优先使用subprocess方式（更稳定）
            if not start_server_subprocess():
                start_server_directly(args.transport, args.host, args.port, args.path)
        else:
            # SSE/HTTP模式使用直接导入方式
            if not start_server_directly(args.transport, args.host, args.port, args.path):
                print("❌ 直接启动失败，请检查配置")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n\n⏹️ MCP服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 