from typing import Dict, Optional
import numpy as np
from langchain.prompts import ChatPromptTemplate
from core.utils.data_logger import DataLogger
from core.utils.llm import get_llm

class PIDOptimizer:
    def __init__(self):
        """初始化PID优化器"""
        self.llm = get_llm()  # 使用统一的 LLM 配置
        
        template = """你是一个专业的PID控制系统专家。基于提供的系统性能指标，你需要给出优化后的PID参数建议。

当前系统状态：
{current_state}

性能指标：
{metrics}

请分析这些数据，并给出优化后的PID参数。
你必须严格按照以下格式输出一个完整的JSON字符串，不要有任何其他内容：
{{
    "kp": 1.0,  
    "ki": 0.1,  
    "kd": 0.05,  
    "explanation": "参数调整的解释"
}}

注意：
1. kp必须在[0.1, 100.0]范围内
2. ki必须在[0.0, 10.0]范围内
3. kd必须在[0.0, 10.0]范围内
4. explanation必须是一个字符串，解释每个参数的调整原因
5. 不要在JSON中使用单引号，使用双引号
6. 不要在JSON中添加注释
7. 不要输出JSON以外的其他内容
"""
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            ("human", "请基于以上信息优化PID参数。")
        ])
    
    def optimize_params(self, channel: int, data_logger: DataLogger, hours: Optional[float] = 1) -> Dict:
        """优化指定通道的PID参数
        
        Args:
            channel: 通道ID
            data_logger: 数据记录器实例
            hours: 分析最近多少小时的数据
            
        Returns:
            优化后的PID参数和解释
        """
        # 获取当前状态
        df = data_logger.get_channel_data(channel, hours)
        if df.empty:
            return {
                "kp": 1.0,
                "ki": 0.1,
                "kd": 0.05,
                "explanation": "没有足够的数据进行优化"
            }
            
        current_state = {
            "kp": df["kp"].iloc[-1],
            "ki": df["ki"].iloc[-1],
            "kd": df["kd"].iloc[-1],
            "target_temp": df["target_temp"].iloc[-1],
            "current_temp": df["temperature"].iloc[-1]
        }
        
        # 获取性能指标
        metrics = data_logger.get_channel_metrics(channel, hours)
        
        # 使用LLM优化参数
        # 格式化当前状态和指标为字符串
        current_state_str = (
            f"- 当前Kp: {current_state['kp']:.3f}\n"
            f"- 当前Ki: {current_state['ki']:.3f}\n"
            f"- 当前Kd: {current_state['kd']:.3f}\n"
            f"- 目标温度: {current_state['target_temp']:.1f}\n"
            f"- 当前温度: {current_state['current_temp']:.1f}"
        )
        
        metrics_str = (
            f"- 上升时间: {metrics.get('rise_time', 'N/A')} 秒\n"
            f"- 超调量: {metrics.get('overshoot', 'N/A')}%\n"
            f"- 稳态误差: {metrics.get('steady_state_error', 'N/A')} 度\n"
            f"- 温度标准差: {metrics.get('temperature_std', 'N/A')} 度"
        )
        
        response = self.llm.invoke(
            self.prompt.format_messages(
                current_state=current_state_str,
                metrics=metrics_str
            )
        )
        
        try:
            import json
            result = json.loads(response.content)  # 将LLM返回的JSON字符串转换为字典
            
            # 验证必要的字段
            required_fields = ['kp', 'ki', 'kd', 'explanation']
            for field in required_fields:
                if field not in result:
                    raise ValueError(f'缺少必要的字段: {field}')
                    
            # 验证字段类型
            if not isinstance(result['kp'], (int, float)):
                raise ValueError('kp 必须是数字')
            if not isinstance(result['ki'], (int, float)):
                raise ValueError('ki 必须是数字')
            if not isinstance(result['kd'], (int, float)):
                raise ValueError('kd 必须是数字')
            if not isinstance(result['explanation'], str):
                raise ValueError('explanation 必须是字符串')
            
            # 确保参数在合理范围内
            result['kp'] = np.clip(float(result['kp']), 0.1, 100.0)
            result['ki'] = np.clip(float(result['ki']), 0.0, 10.0)
            result['kd'] = np.clip(float(result['kd']), 0.0, 10.0)
            return result
        except Exception as e:
            print(f"解析LLM响应时出错: {str(e)}")
            return {
                "kp": current_state["kp"],
                "ki": current_state["ki"],
                "kd": current_state["kd"],
                "explanation": "参数优化失败，保持当前参数不变"
            }
