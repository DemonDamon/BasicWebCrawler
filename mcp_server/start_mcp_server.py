#!/usr/bin/env python3
"""
BasicWebCrawler MCP服务器启动脚本

快速启动MCP服务器的便捷脚本
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = ['fastmcp', 'requests', 'beautifulsoup4', 'markdownify']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装依赖:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 BasicWebCrawler MCP服务器启动器")
    print("=" * 50)
    
    # 检查依赖
    print("📦 检查依赖包...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ 所有依赖包已安装")
    
    # 检查MCP服务器文件
    mcp_server_file = Path(__file__).parent / "mcp_server.py"
    if not mcp_server_file.exists():
        print("❌ 找不到 mcp_server.py 文件")
        sys.exit(1)
    
    print(f"📄 MCP服务器文件: {mcp_server_file}")
    
    # 显示配置信息
    print("\n🔧 配置信息:")
    print(f"   工作目录: {Path.cwd()}")
    print(f"   Python版本: {sys.version.split()[0]}")
    
    # 显示AI助手配置示例
    print("\n🤖 AI助手配置示例:")
    print("=" * 30)
    
    # 使用项目根目录作为工作目录
    project_root = str(Path(__file__).parent.parent).replace("\\", "/")
    mcp_server_path = str(mcp_server_file).replace("\\", "/")
    
    print("Claude Desktop 配置:")
    claude_config = f'''{{
  "mcpServers": {{
    "basic-web-crawler": {{
      "command": "python",
      "args": ["{mcp_server_path}"],
      "cwd": "{project_root}"
    }}
  }}
}}'''
    print(claude_config)
    
    print("\nCursor 配置:")
    cursor_config = f'''{{
  "mcpServers": {{
    "basic-web-crawler": {{
      "command": "python",
      "args": ["{mcp_server_path}"],
      "cwd": "{project_root}"
    }}
  }}
}}'''
    print(cursor_config)
    
    # 询问是否启动服务器
    print("\n" + "=" * 50)
    choice = input("是否现在启动MCP服务器? (y/n): ").strip().lower()
    
    if choice in ['y', 'yes', '是']:
        print("\n🚀 启动MCP服务器...")
        print("提示: 按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        try:
            # 切换到项目根目录启动MCP服务器
            os.chdir(project_root)
            subprocess.run([sys.executable, str(mcp_server_file)], check=True)
        except KeyboardInterrupt:
            print("\n\n⏹️ MCP服务器已停止")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ MCP服务器启动失败: {e}")
            sys.exit(1)
    else:
        print("\n📝 手动启动命令:")
        print(f"cd {project_root}")
        print(f"python {mcp_server_path}")
        print("\n或使用FastMCP CLI:")
        print(f"cd {project_root}")
        print(f"fastmcp run {mcp_server_path}")

if __name__ == "__main__":
    main() 