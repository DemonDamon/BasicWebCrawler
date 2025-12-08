#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试百炼 qwen-plus-latest 模型
"""

import sys
from pathlib import Path

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent))

from llm_client import LLMClientFactory

def test_qwen_plus_latest():
    """测试 qwen-plus-latest 模型"""
    print("=" * 70)
    print("测试百炼 qwen-plus-latest 模型")
    print("=" * 70)
    
    try:
        # 加载环境变量
        LLMClientFactory.load_env_config()
        
        # 创建百炼客户端，使用 qwen-plus-latest 模型
        print("\n1. 创建百炼客户端...")
        client = LLMClientFactory.create_client(
            provider="bailian",
            model_name="qwen-plus-latest"
        )
        print(f"✅ 客户端创建成功")
        print(f"   模型名称: {client.model_name}")
        print(f"   API端点: {client.base_url}")
        
        # 测试简单消息
        print("\n2. 发送测试消息...")
        test_message = "你好，请简单介绍一下你自己"
        messages = [{"role": "user", "content": test_message}]
        
        print(f"   测试消息: {test_message}")
        print("   正在等待响应...")
        
        result = client.chat_completion(messages)
        
        if result.get("error"):
            print(f"\n❌ 测试失败: {result['error']}")
            return False
        else:
            print(f"\n✅ 测试成功!")
            print(f"   响应时间: {result.get('response_time', 'N/A')}秒")
            print(f"   模型: {result.get('model', 'N/A')}")
            print(f"   响应模型: {result.get('response_model', 'N/A')}")
            print(f"   回答: {result.get('content', '')[:200]}...")
            return True
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_qwen_plus_latest()
    sys.exit(0 if success else 1)

