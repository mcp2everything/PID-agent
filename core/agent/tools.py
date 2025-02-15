from langchain.tools import BaseTool
from typing import Optional, Dict, List
import numpy as np
import json  # 移到全局导入
import traceback  # 添加traceback导入
from datetime import datetime, timedelta
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.utils.data_logger import DataLogger
from core.utils.pid_optimizer import PIDOptimizer

class TemperatureAnalysisTool(BaseTool):
    name: str = "temperature_curve_analysis"
    description: str = """分析温度曲线特性的工具。输入参数: {"channel": <通道ID>}。
    分析指标包括：上升时间、超调量、稳态误差、温度波动等。"""
    
    def __init__(self, data_logger: DataLogger, **kwargs):
        super().__init__(**kwargs)
        self._data_logger = data_logger
    
    def _run(self, channel: str, hours: Optional[float] = 1) -> str:
        try:
            # 改进channel参数处理
            if isinstance(channel, dict):
                channel_id = int(channel.get('channel', 0))
            elif isinstance(channel, str):
                try:
                    channel_data = json.loads(channel)
                    channel_id = int(channel_data.get('channel', 0))
                except json.JSONDecodeError:
                    channel_id = int(channel)
            else:
                channel_id = int(channel)
                
            print(f"\nDebug - TemperatureAnalysisTool 分析通道 {channel_id}:")
            
            # 获取通道数据并验证
            df = self._data_logger.get_channel_data(channel_id, hours)
            print(f"获取到的DataFrame: 行数={len(df)}, 列={df.columns.tolist() if not df.empty else '空'}")
            
            if df.empty or 'temperature' not in df.columns:
                print("无有效温度数据")
                return "无数据可分析"
                
            # 将DataFrame数据转换为numpy数组进行分析
            temp_series = df['temperature']
            temp_data = temp_series.values
            target_temp = float(df['target_temp'].iloc[-1])
            
            print(f"温度数据点数: {len(temp_data)}")
            print(f"温度数据范围: {temp_data.min():.2f} - {temp_data.max():.2f}")
            print(f"目标温度: {target_temp}")
            
            # 确保所有数值都是原生Python类型
            metrics = {
                "current_temp": float(temp_data[-1]),
                "target_temp": float(target_temp),
                "max_temp": float(np.max(temp_data)),
                "min_temp": float(np.min(temp_data)),
                "avg_temp": float(np.mean(temp_data)),
                "temp_std": float(np.std(temp_data)),
                "steady_state": float(np.mean(temp_data[-5:])),
                "data_points": int(len(temp_data))
            }
            
            # 计算性能指标
            metrics["steady_error"] = float(metrics["target_temp"] - metrics["steady_state"])
            metrics["overshoot"] = float(((metrics["max_temp"] - metrics["target_temp"]) / metrics["target_temp"]) * 100)
            
            # 计算上升时间
            temp_range = metrics["max_temp"] - metrics["min_temp"]
            t_90 = metrics["min_temp"] + 0.9 * temp_range
            rise_indices = np.where(temp_data >= t_90)[0]
            metrics["rise_time"] = int(rise_indices[0]) if len(rise_indices) > 0 else None
            
            print(f"分析结果: {json.dumps(metrics, indent=2)}")
            return json.dumps(metrics)
            
        except Exception as e:
            print(f"分析失败，错误: {str(e)}")
            print(f"错误堆栈: {traceback.format_exc()}")
            return f"分析失败: {str(e)}"

class PIDOptimizationTool(BaseTool):
    name: str = "pid_parameter_optimization"
    description: str = """优化PID参数的工具。输入参数: {"channel": <通道ID>}。
    基于温度曲线分析结果，给出具体的PID参数调整建议。"""
    
    def __init__(self, data_logger: DataLogger, **kwargs):
        super().__init__(**kwargs)
        self._data_logger = data_logger
        self._optimizer = PIDOptimizer()
    
    def _run(self, channel: str, hours: Optional[float] = 1) -> str:
        try:
            # 改进channel参数处理
            if isinstance(channel, dict):
                channel_id = int(channel.get('channel', 0))
            elif isinstance(channel, str):
                try:
                    channel_data = json.loads(channel)
                    channel_id = int(channel_data.get('channel', 0))
                except json.JSONDecodeError:
                    channel_id = int(channel)
            else:
                channel_id = int(channel)
                
            print(f"\nDebug - PIDOptimizationTool 分析通道 {channel_id}:")
            
            df = self._data_logger.get_channel_data(channel_id, hours)
            print(f"获取到的DataFrame: 行数={len(df)}, 列={df.columns.tolist() if not df.empty else '空'}")
            
            if df.empty or 'temperature' not in df.columns:
                print("无有效温度数据")
                return "无数据可分析"
            
            # 提取当前PID参数
            current_params = {
                "kp": float(df['kp'].iloc[-1]),
                "ki": float(df['ki'].iloc[-1]),
                "kd": float(df['kd'].iloc[-1]),
                "target_temp": float(df['target_temp'].iloc[-1])
            }
            
            # 计算性能指标
            temp_data = df['temperature'].values
            temp_std = float(np.std(temp_data))
            steady_error = float(current_params["target_temp"] - np.mean(temp_data[-5:]))
            
            # 生成调优建议
            analysis_result = {
                "current_params": current_params,
                "performance": {
                    "steady_error": steady_error,
                    "stability": temp_std,
                    "data_points": len(temp_data)
                },
                "status": {
                    "response_speed": "fast" if len(temp_data) > 0 and temp_data[-1] >= current_params["target_temp"] * 0.9 else "slow",
                    "stability": "stable" if temp_std < 0.5 else "unstable",
                    "accuracy": "good" if abs(steady_error) < 0.5 else "poor"
                }
            }
            
            print(f"优化分析结果: {json.dumps(analysis_result, indent=2)}")
            return json.dumps(analysis_result)
            
        except Exception as e:
            print(f"优化分析失败，错误: {str(e)}")
            print(f"错误堆栈: {traceback.format_exc()}")
            return f"优化分析失败: {str(e)}"

def get_tools(data_logger: DataLogger) -> List[BaseTool]:
    """创建工具实例
    
    Args:
        data_logger: 数据记录器实例，用于共享数据
        
    Returns:
        工具列表
    """
    return [
        TemperatureAnalysisTool(data_logger=data_logger),
        PIDOptimizationTool(data_logger=data_logger)
    ]
