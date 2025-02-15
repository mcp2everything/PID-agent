"""LLM连接性测试工具"""

from typing import Dict, Tuple
from .llm import get_llm
from langchain.schema import HumanMessage

async def test_llm_connection() -> Tuple[bool, str]:
    """
    测试LLM连接性
    
    Returns:
        Tuple[bool, str]: (是否连接成功, 详细信息)
    """
    try:
        # 获取LLM实例
        llm = get_llm()
        
        # 发送一个简单的测试消息
        test_message = [HumanMessage(content="Hi, this is a test message. Please respond with 'OK'.")]
        response = llm.invoke(test_message)
        
        # 检查响应
        if response and hasattr(response, 'content'):
            return True, "LLM连接测试成功"
        else:
            return False, "LLM响应格式异常"
            
    except ValueError as e:
        # 配置错误
        return False, f"配置错误: {str(e)}"
    except Exception as e:
        # 其他错误（网络、认证等）
        return False, f"连接失败: {str(e)}"
