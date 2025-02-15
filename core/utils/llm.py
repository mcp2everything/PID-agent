"""LLM工具函数"""

import os
from typing import Dict, Optional

def get_llm():
    """根据配置创建LLM实例"""
    from config.llm_settings import llm_settings
    
    # 获取当前配置
    current_config = llm_settings.get_current_config()
    if not current_config["provider"]:
        raise ValueError("No LLM provider configured. Please configure one in the UI first.")
    
    provider = current_config["provider"]
    model = current_config["model"]
    
    # 获取提供商配置
    provider_config = llm_settings.get_provider_config(provider)
    if not provider_config:
        raise ValueError(f"Provider {provider} not configured")
    
    # 获取模型配置
    model_config = llm_settings.get_model_config(provider, model)
    if not model_config:
        raise ValueError(f"Model {model} not found for provider {provider}")
    
    # 根据提供商创建相应的LLM实例
    if provider == "deepseek":
        from langchain_deepseek import ChatDeepSeek
        return ChatDeepSeek(
            temperature=0.3,
            max_tokens=model_config["max_tokens"],
            model=model,
            api_key=provider_config["api_key"] or os.getenv("DEEPSEEK_API_KEY"),
            base_url=provider_config["base_url"],
            streaming=False,
            request_timeout=60
        )
    elif provider == "qwen":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            temperature=0.3,
            model=model,
            max_tokens=model_config["max_tokens"],
            openai_api_key=provider_config["api_key"] or os.getenv("DASHSCOPE_API_KEY"),
            openai_api_base=provider_config["base_url"] or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            streaming=False,
            request_timeout=60
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0.3,
            max_output_tokens=model_config["max_tokens"],
            google_api_key=provider_config["api_key"] or os.getenv("GEMINI_API_KEY"),
            streaming=False,
            convert_system_message_to_human=True  # Gemini不支持系统消息
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            temperature=0.3,
            model=model,
            max_tokens=model_config["max_tokens"],
            openai_api_key=provider_config["api_key"] or os.getenv("OPENAI_API_KEY"),
            openai_api_base=provider_config["base_url"] or os.getenv("OPENAI_API_BASE"),
            streaming=False,
            request_timeout=60
        )
    
    raise ValueError(f"Unsupported LLM provider: {provider}")
