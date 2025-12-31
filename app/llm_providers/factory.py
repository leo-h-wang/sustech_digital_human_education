"""LLM 客户端工厂"""
import os
from typing import Optional
from app.llm_providers.base import LLMClient
from app.llm_providers.tongyi import TongyiClient


def create_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    创建 LLM 客户端实例
    
    Args:
        provider: 提供商名称（tongyi, spark, kimi等），如果为None则从环境变量获取
        
    Returns:
        LLMClient 实例
    """
    provider = provider or os.getenv("LLM_PROVIDER", "tongyi").lower()
    
    if provider == "tongyi":
        return TongyiClient()
    elif provider == "spark":
        # TODO: 实现星火客户端
        raise NotImplementedError("星火客户端尚未实现")
    elif provider == "kimi":
        # TODO: 实现 Kimi 客户端
        raise NotImplementedError("Kimi 客户端尚未实现")
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")

