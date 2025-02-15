from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_deepseek import ChatDeepSeek
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from core.utils.data_logger import DataLogger
from core.agent.tools import get_tools
class PIDAgent:
    def __init__(self, num_channels: int = 16):
        """初始化PID代理
        
        Args:
            num_channels: 支持的通道数量
        """
        from config.settings import settings
        
        self.num_channels = num_channels
        self.data_logger = DataLogger(num_channels)
        
        self.llm = ChatDeepSeek(
            temperature=0.2,
            max_tokens=2048,
            model='deepseek-chat',
            api_key=settings.DEEPSEEK_API_KEY
        )
        
        self.tools = get_tools(self.data_logger)
        
        prompt_template = '''你是一个专业的PID参数优化专家。你有以下工具可以使用：

可用工具: {tool_names}

工具详情:
{tools}

当前状态信息：
- 通道ID：{channel}
- 分析时间范围：最近{hours}小时的数据

请按照以下步骤进行分析和优化建议：
1. 先使用 temperature_curve_analysis 工具分析当前系统的响应特性
2. 再使用 pid_parameter_optimization 工具评估当前PID参数并获取优化建议
3. 最后给出具体的参数调整建议，并解释原因

Human: {input}

Assistant: Let's analyze this step by step.

{agent_scratchpad}'''
        
        self.prompt = PromptTemplate.from_template(prompt_template)
        
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def log_data(self, data: Dict):
        """记录所有通道的数据
        
        Args:
            data: 包含所有通道数据的字典
        """
        self.data_logger.log_data(data)
    
    def analyze_channel(self, channel: int, hours: Optional[float] = 1) -> Dict:
        """分析指定通道的温度曲线
        
        Args:
            channel: 通道ID
            hours: 分析最近多少小时的数据
            
        Returns:
            包含分析结果的字典
        """
        if not (0 <= channel < self.num_channels):
            return {
                'error': f'通道ID {channel} 超出范围 [0, {self.num_channels-1}]'
            }
        
        print(f"\n开始分析通道 {channel} 的数据...")
        
        # 使用工具分析温度曲线
        print("步骤1: 分析温度曲线...")
        temp_analysis = self.tools[0]
        curve_analysis = temp_analysis._run(channel, hours)
        print(f"曲线分析结果: {curve_analysis}")
        
        # 使用工具优化PID参数
        print("\n步骤2: 优化PID参数...")
        pid_optimizer = self.tools[1]
        params_optimization = pid_optimizer._run(channel, hours)
        print(f"PID优化结果: {params_optimization}")
        
        # 使用DeepSeek模型生成综合建议
        print("\n步骤3: 生成AI综合建议...")
        response = self.agent_executor.invoke({
            'input': f"分析通道{channel}的温度曲线和PID参数",
            'channel': channel,
            'hours': hours,
            'agent_scratchpad': "",
            'tools': str(self.tools),
            'tool_names': ', '.join([tool.name for tool in self.tools])
        })
        print(f"AI响应: {response}")
        
        return {
            'channel': channel,
            'curve_analysis': curve_analysis,
            'params_optimization': params_optimization,
            'ai_suggestion': response['output'],
            'timestamp': datetime.now().isoformat()
        }
    
    def analyze_all_channels(self, hours: Optional[float] = 1) -> List[Dict]:
        """分析所有通道的温度曲线
        
        Args:
            hours: 分析最近多少小时的数据
            
        Returns:
            每个通道的分析结果列表
        """
        return [
            self.analyze_channel(channel, hours)
            for channel in range(self.num_channels)
        ]


def generate_mock_data(target_temp=100, duration_seconds=60, sample_rate_hz=10):
    """生成模拟的温度数据
    
    Args:
        target_temp: 目标温度
        duration_seconds: 模拟时长（秒）
        sample_rate_hz: 采样率（Hz）
    
    Returns:
        包含温度数据的DataFrame
    """
    timestamps = [datetime.now() + timedelta(seconds=i/sample_rate_hz) 
                 for i in range(duration_seconds * sample_rate_hz)]
    
    # 模拟PID控制的温度响应
    time_points = np.linspace(0, duration_seconds, len(timestamps))
    temp_response = target_temp * (1 - np.exp(-0.2 * time_points)) + \
                   5 * np.sin(0.5 * time_points) * np.exp(-0.1 * time_points)
    
    # 添加一些随机噪声
    temp_response += np.random.normal(0, 0.5, len(temp_response))
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'temperature': temp_response
    })


if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # 初始PID Agent
    agent = PIDAgent(num_channels=16)
    
    # 模拟多通道数据
    data = {
        'timestamp': datetime.now().isoformat(),
        'channels': []
    }
    
    # 为每个通道设置不同的参数
    for i in range(16):
        data['channels'].append({
            'id': i,
            'temperature': 25.0 + i,  # 每个通道初始温度不同
            'pid_params': {
                'kp': 1.0 + i * 0.1,
                'ki': 0.1 + i * 0.01,
                'kd': 0.05 + i * 0.005,
                'target_temp': 50.0 + i * 2,
                'control_period': 100 + i * 10,  # 从100ms到250ms
                'max_duty': 60 + i * 2  # 从60%到90%
            },
            'heating': i % 2 == 0  # 奇数通道加热，偶数通道不加热
        })
    
    # 记录数据
    agent.log_data(data)
    
    # 分析3个通道
    for channel_id in [0, 1, 2]:  # 只测试前3个通道
        print(f"\n=== 分析通道 {channel_id} ===" )
        analysis = agent.analyze_channel(channel_id, hours=1)
        if 'error' in analysis:
            print(f"错误: {analysis['error']}")
            continue
            
        print("\n1. 温度曲线分析:")
        print(analysis['curve_analysis'])
        print("\n2. PID参数优化建议:")
        print(analysis['params_optimization'])
        print("\n3. AI综合建议:")
        print(analysis['ai_suggestion'])
