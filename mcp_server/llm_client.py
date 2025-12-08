#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四大厂商大模型客户端脚本
支持硅基流动、DeepSeek、百炼、Kimi四大厂商的API调用
作者：自动生成
日期：2025年
"""

import os
import sys
import json
import time
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv
import requests
from openai import OpenAI

# 配置日志
# 注意：在 MCP 模式下，stdout 用于 JSON-RPC 通信，不能用于日志输出
# 所以这里使用 stderr 和文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # 改为 stderr，避免干扰 MCP 通信
        logging.FileHandler('llm_client.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class LLMClient(ABC):
    """大模型客户端基类"""
    
    def __init__(self, api_key: str, base_url: str, model_name: str, timeout: int = 120):
        """
        初始化客户端
        
        Args:
            api_key (str): API密钥
            base_url (str): API基础URL
            model_name (str): 模型名称
            timeout (int): 请求超时时间（秒），默认120秒
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化OpenAI客户端"""
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info(f"初始化 {self.__class__.__name__} 客户端成功")
        except Exception as e:
            logger.error(f"初始化 {self.__class__.__name__} 客户端失败: {e}")
            raise
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取厂商名称"""
        pass
    
    def chat_completion(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        发送聊天完成请求
        
        Args:
            messages (List[Dict[str, str]]): 消息列表
            stream (bool): 是否使用流式返回，默认False
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: API响应结果
        """
        try:
            logger.info(f"向 {self.get_provider_name()} 发送请求...")
            logger.info(f"🔍 请求模型: {self.model_name}")
            logger.info(f"🔍 API端点: {self.base_url}")
            logger.info(f"🔍 流式模式: {stream}")
            
            if stream:
                return self._stream_completion(messages, **kwargs)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=False,
                **kwargs
            )
            
            # 记录响应中的模型信息
            response_model = getattr(response, 'model', None) or getattr(response, 'model_name', None)
            logger.info(f"🔍 响应模型: {response_model}")
            
            result = {
                "provider": self.get_provider_name(),
                "model": self.model_name,
                "response_model": response_model,
                "content": response.choices[0].message.content,
                "usage": response.usage.dict() if response.usage else None,
                "finish_reason": response.choices[0].finish_reason
            }
            
            # 检查模型名称是否匹配
            if response_model and response_model != self.model_name:
                logger.warning(f"⚠️ 模型名称不匹配! 请求: {self.model_name}, 返回: {response_model}")
                logger.warning("🚨 可能存在兜底机制!")
            
            logger.info(f"{self.get_provider_name()} 请求成功")
            return result
            
        except Exception as e:
            logger.error(f"{self.get_provider_name()} 请求失败: {e}")
            return {
                "provider": self.get_provider_name(),
                "model": self.model_name,
                "error": str(e),
                "content": None
            }
    
    def _stream_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        流式聊天完成请求
        
        Args:
            messages (List[Dict[str, str]]): 消息列表
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: API响应结果
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            # 收集流式响应
            full_content = []
            finish_reason = None
            response_model = None
            
            logger.info(f"开始接收 {self.get_provider_name()} 流式响应...")
            chunk_count = 0
            
            for chunk in response:
                chunk_count += 1
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        full_content.append(delta.content)
                        # 每50个chunk输出一次进度
                        if chunk_count % 50 == 0:
                            logger.info(f"  已接收 {chunk_count} 个chunk, 当前内容长度: {len(''.join(full_content))} 字符")
                    
                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                
                # 获取模型名称
                if hasattr(chunk, 'model') and chunk.model:
                    response_model = chunk.model
            
            content = ''.join(full_content)
            logger.info(f"✅ 流式响应完成，共 {chunk_count} 个chunk，总内容长度: {len(content)} 字符")
            
            result = {
                "provider": self.get_provider_name(),
                "model": self.model_name,
                "response_model": response_model,
                "content": content,
                "usage": None,  # 流式模式下通常没有usage信息
                "finish_reason": finish_reason
            }
            
            logger.info(f"{self.get_provider_name()} 流式请求成功")
            return result
            
        except Exception as e:
            logger.error(f"{self.get_provider_name()} 流式请求失败: {e}")
            return {
                "provider": self.get_provider_name(),
                "model": self.model_name,
                "error": str(e),
                "content": None
            }
    
    def test_connectivity(self, test_message: str = "你是谁") -> Dict[str, Any]:
        """
        测试连通性
        
        Args:
            test_message (str): 测试消息
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        messages = [{"role": "user", "content": test_message}]
        start_time = time.time()
        result = self.chat_completion(messages)
        end_time = time.time()
        
        result["response_time"] = round(end_time - start_time, 2)
        result["test_message"] = test_message
        
        return result


class SiliconFlowClient(LLMClient):
    """硅基流动客户端"""
    
    def __init__(self, api_key: str, model_name: str = "Qwen/Qwen3-32B", timeout: int = 30):
        super().__init__(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1",
            model_name=model_name,
            timeout=timeout
        )
    
    def get_provider_name(self) -> str:
        return "硅基流动"


class DeepSeekClient(LLMClient):
    """DeepSeek客户端"""
    
    def __init__(self, api_key: str, model_name: str = "deepseek-chat", timeout: int = 30):
        super().__init__(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            model_name=model_name,
            timeout=timeout
        )
    
    def get_provider_name(self) -> str:
        return "DeepSeek"


class BailianClient(LLMClient):
    """百炼客户端"""
    
    def __init__(self, api_key: str, model_name: str = "qwen3-max", timeout: int = 30):
        super().__init__(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model_name=model_name,
            timeout=timeout
        )
    
    def get_provider_name(self) -> str:
        return "百炼"


class KimiClient(LLMClient):
    """Kimi客户端"""
    
    def __init__(self, api_key: str, model_name: str = "kimi-latest", timeout: int = 30):
        super().__init__(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
            model_name=model_name,
            timeout=timeout
        )
    
    def get_provider_name(self) -> str:
        return "Kimi"


class LLMClientFactory:
    """大模型客户端工厂类"""
    
    # 厂商配置
    PROVIDERS = {
        "siliconflow": {
            "class": SiliconFlowClient,
            "env_key": "SILICONFLOW_API_KEY",
            "default_model": "Qwen/Qwen3-32B"
        },
        "deepseek": {
            "class": DeepSeekClient,
            "env_key": "DEEPSEEK_API_KEY",
            "default_model": "deepseek-chat"
        },
        "bailian": {
            "class": BailianClient,
            "env_key": "BAILIAN_API_KEY",
            "default_model": "qwen3-max"
        },
        "kimi": {
            "class": KimiClient,
            "env_key": "KIMI_API_KEY",
            "default_model": "kimi-latest"
        }
    }
    
    @classmethod
    def load_env_config(cls, env_file_path: str = None) -> Dict[str, str]:
        """
        加载环境变量配置
        
        Args:
            env_file_path (str): .env文件路径
            
        Returns:
            Dict[str, str]: 环境变量字典
        """
        if env_file_path is None:
            # 默认使用当前脚本所在目录的.env文件
            current_dir = Path(__file__).parent
            env_file_path = current_dir / ".env"
        
        if os.path.exists(env_file_path):
            load_dotenv(env_file_path)
            logger.info(f"成功加载环境变量文件: {env_file_path}")
        else:
            logger.warning(f"环境变量文件不存在: {env_file_path}")
        
        # 返回所有相关的API密钥
        env_config = {}
        for provider, config in cls.PROVIDERS.items():
            env_key = config["env_key"]
            api_key = os.getenv(env_key)
            if api_key:
                env_config[provider] = api_key
                logger.info(f"成功加载 {provider} API密钥")
            else:
                logger.warning(f"未找到 {provider} API密钥: {env_key}")
        
        return env_config
    
    @classmethod
    def create_client(cls, provider: str, api_key: str = None, model_name: str = None, **kwargs) -> LLMClient:
        """
        创建指定厂商的客户端
        
        Args:
            provider (str): 厂商名称
            api_key (str): API密钥，如果为None则从环境变量读取
            model_name (str): 模型名称，如果为None则使用默认模型
            **kwargs: 其他参数
            
        Returns:
            LLMClient: 客户端实例
        """
        if provider not in cls.PROVIDERS:
            raise ValueError(f"不支持的厂商: {provider}，支持的厂商: {list(cls.PROVIDERS.keys())}")
        
        provider_config = cls.PROVIDERS[provider]
        
        # 获取API密钥
        if api_key is None:
            api_key = os.getenv(provider_config["env_key"])
            if not api_key:
                raise ValueError(f"未找到 {provider} 的API密钥: {provider_config['env_key']}")
        
        # 获取模型名称
        if model_name is None:
            model_name = provider_config["default_model"]
        
        # 创建客户端实例
        client_class = provider_config["class"]
        return client_class(api_key=api_key, model_name=model_name, **kwargs)
    
    @classmethod
    def create_all_clients(cls, env_config: Dict[str, str] = None, **kwargs) -> Dict[str, LLMClient]:
        """
        创建所有可用厂商的客户端
        
        Args:
            env_config (Dict[str, str]): 环境变量配置
            **kwargs: 其他参数
            
        Returns:
            Dict[str, LLMClient]: 客户端字典
        """
        if env_config is None:
            env_config = cls.load_env_config()
        
        clients = {}
        for provider in cls.PROVIDERS.keys():
            if provider in env_config:
                try:
                    client = cls.create_client(provider, api_key=env_config[provider], **kwargs)
                    clients[provider] = client
                    logger.info(f"成功创建 {provider} 客户端")
                except Exception as e:
                    logger.error(f"创建 {provider} 客户端失败: {e}")
            else:
                logger.warning(f"跳过 {provider}，未找到API密钥")
        
        return clients


def test_all_providers(test_message: str = "你是谁") -> Dict[str, Any]:
    """
    测试所有厂商的连通性
    
    Args:
        test_message (str): 测试消息
        
    Returns:
        Dict[str, Any]: 测试结果
    """
    logger.info("=" * 60)
    logger.info("开始测试四大厂商连通性")
    logger.info("=" * 60)
    
    # 加载环境变量
    env_config = LLMClientFactory.load_env_config()
    
    if not env_config:
        logger.error("未找到任何API密钥，请检查.env文件")
        return {"error": "未找到任何API密钥"}
    
    # 创建所有客户端
    clients = LLMClientFactory.create_all_clients(env_config)
    
    if not clients:
        logger.error("未能创建任何客户端")
        return {"error": "未能创建任何客户端"}
    
    # 测试每个客户端
    results = {}
    for provider, client in clients.items():
        logger.info(f"\n测试 {client.get_provider_name()} ...")
        result = client.test_connectivity(test_message)
        results[provider] = result
        
        # 打印结果
        if result.get("error"):
            logger.error(f"❌ {client.get_provider_name()} 测试失败: {result['error']}")
        else:
            logger.info(f"✅ {client.get_provider_name()} 测试成功")
            logger.info(f"   响应时间: {result['response_time']}秒")
            logger.info(f"   模型: {result['model']}")
            logger.info(f"   回答: {result['content'][:100]}...")
    
    return results


def main():
    """主函数"""
    logger.info("四大厂商大模型客户端测试程序")
    
    try:
        # 测试所有厂商连通性
        results = test_all_providers("你是谁")
        
        # 统计结果
        total_providers = len(LLMClientFactory.PROVIDERS)
        successful_tests = len([r for r in results.values() if not r.get("error")])
        failed_tests = len([r for r in results.values() if r.get("error")])
        
        logger.info("\n" + "=" * 60)
        logger.info("测试结果汇总")
        logger.info("=" * 60)
        logger.info(f"总厂商数: {total_providers}")
        logger.info(f"成功测试: {successful_tests}")
        logger.info(f"失败测试: {failed_tests}")
        
        if successful_tests > 0:
            logger.info("\n✅ 成功的厂商:")
            for provider, result in results.items():
                if not result.get("error"):
                    logger.info(f"  - {result['provider']}: {result['response_time']}秒")
        
        if failed_tests > 0:
            logger.info("\n❌ 失败的厂商:")
            for provider, result in results.items():
                if result.get("error"):
                    logger.info(f"  - {result.get('provider', provider)}: {result['error']}")
        
        # 保存结果到文件
        output_file = "connectivity_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"\n测试结果已保存到: {output_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return {"error": str(e)}


# 便捷函数，供其他脚本调用
def get_client(provider: str = "deepseek", **kwargs) -> LLMClient:
    """
    获取指定厂商的客户端（便捷函数）
    
    Args:
        provider (str): 厂商名称，默认为deepseek
        **kwargs: 其他参数
        
    Returns:
        LLMClient: 客户端实例
    """
    LLMClientFactory.load_env_config()
    return LLMClientFactory.create_client(provider, **kwargs)


# 为了兼容性，提供各厂商的便捷函数
def siliconflow(**kwargs) -> SiliconFlowClient:
    """获取硅基流动客户端"""
    return get_client("siliconflow", **kwargs)


def deepseek(**kwargs) -> DeepSeekClient:
    """获取DeepSeek客户端"""
    return get_client("deepseek", **kwargs)


def bailian(**kwargs) -> BailianClient:
    """获取百炼客户端"""
    return get_client("bailian", **kwargs)


def kimi(**kwargs) -> KimiClient:
    """获取Kimi客户端"""
    return get_client("kimi", **kwargs)


if __name__ == "__main__":
    main()