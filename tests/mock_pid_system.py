import numpy as np
from typing import Dict, Tuple, Optional
import time
from datetime import datetime

class MockPIDSystem:
    def __init__(self, num_channels: int = 16):
        # 初始化多通道系统
        self.num_channels = num_channels
        self.channels = {}
        
        for i in range(num_channels):
            self.channels[i] = {
                'current_temp': 25.0,
                'target_temp': 25.0,
                'kp': 1.0,
                'ki': 0.1,
                'kd': 0.05,
                'control_period': 100,  # 默认100ms
                'max_duty': 100,       # 默认100%
                'heating': False,
                'last_error': 0.0,
                'integral': 0.0,
                'last_time': time.time(),
                'last_control_time': time.time()
            }
        
        # 系统参数
        self.time_constant = 5.0  # 系统时间常数
        self.sample_time = 0.1    # 采样时间
        self.max_power = 100.0    # 最大加热功率
        
        # 添加一些噪声和干扰
        self.noise_amplitude = 0.1
        self.disturbance = {i: 0.0 for i in range(num_channels)}
    
    def update_params(self, channel: int, kp: float, ki: float, kd: float, target: float, 
                     control_period: int = 100, max_duty: int = 100):
        """更新指定通道的PID参数和目标温度"""
        if 0 <= channel < self.num_channels:
            # 验证参数范围
            control_period = np.clip(control_period, 10, 1000)
            max_duty = np.clip(max_duty, 0, 100)
            
            self.channels[channel].update({
                'kp': kp,
                'ki': ki,
                'kd': kd,
                'target_temp': target,
                'control_period': control_period,
                'max_duty': max_duty
            })
    
    def _calculate_next_temp(self, channel: int) -> float:
        """计算指定通道的下一个温度值"""
        if not (0 <= channel < self.num_channels):
            return 25.0
            
        ch = self.channels[channel]
        current_time = time.time()
        dt = current_time - ch['last_time']
        
        if dt < self.sample_time:
            return ch['current_temp']
        
        if not ch['heating']:
            # 如果没有加热，模拟自然冷却
            temp_change = -0.1 * (ch['current_temp'] - 25.0) * (dt / self.time_constant)
            new_temp = ch['current_temp'] + temp_change
            ch['last_time'] = current_time
            return new_temp
            
        # 计算PID误差
        error = ch['target_temp'] - ch['current_temp']
        
        # 比例项
        p_term = ch['kp'] * error
        
        # 积分项
        ch['integral'] += error * dt
        i_term = ch['ki'] * ch['integral']
        
        # 微分项
        d_term = 0.0
        if dt > 0:
            d_term = ch['kd'] * (error - ch['last_error']) / dt
            
        # 检查是否到达控制周期
        if current_time - ch['last_control_time'] < ch['control_period'] / 1000:
            return ch['current_temp']
        ch['last_control_time'] = current_time
        
        # 计算控制输出并应用最大占空比限制
        output = p_term + i_term + d_term
        max_output = self.max_power * (ch['max_duty'] / 100)
        output = np.clip(output, 0, max_output)
        
        # 模拟温度变化（一阶系统）
        temp_change = (output / self.max_power * (ch['target_temp'] - ch['current_temp']) 
                      + self.disturbance[channel]) * (dt / self.time_constant)
        
        # 添加随机噪声
        noise = np.random.normal(0, self.noise_amplitude)
        
        new_temp = ch['current_temp'] + temp_change + noise
        
        # 更新状态
        ch['last_error'] = error
        ch['last_time'] = current_time
        
        return new_temp
    
    def get_current_state(self) -> Dict:
        """获取所有通道的当前系统状态"""
        channels = []
        for i in range(self.num_channels):
            ch = self.channels[i]
            ch['current_temp'] = self._calculate_next_temp(i)
            
            channels.append({
                "id": i,
                "temperature": round(ch['current_temp'], 2),
                "pid_params": {
                    "kp": ch['kp'],
                    "ki": ch['ki'],
                    "kd": ch['kd'],
                    "target_temp": ch['target_temp'],
                    "control_period": ch['control_period'],
                    "max_duty": ch['max_duty']
                },
                "heating": ch['heating']
            })
        
        return {
            "channels": channels,
            "timestamp": datetime.now().isoformat(),
            "status": "running"
        }
    
    def add_disturbance(self, channel: int, magnitude: float = 1.0):
        """为指定通道添加外部干扰"""
        if 0 <= channel < self.num_channels:
            self.disturbance[channel] = magnitude * np.random.randn()
    
    def reset(self, channel: Optional[int] = None):
        """重置系统状态
        
        Args:
            channel: 如果指定，只重置该通道；否则重置所有通道
        """
        if channel is not None and 0 <= channel < self.num_channels:
            self.channels[channel].update({
                'current_temp': 25.0,
                'integral': 0.0,
                'last_error': 0.0,
                'heating': False
            })
            self.disturbance[channel] = 0.0
        else:
            for i in range(self.num_channels):
                self.channels[i].update({
                    'current_temp': 25.0,
                    'integral': 0.0,
                    'last_error': 0.0,
                    'heating': False
                })
                self.disturbance[i] = 0.0
    
    def set_heating(self, channel: int, heating: bool):
        """设置指定通道的加热状态"""
        if 0 <= channel < self.num_channels:
            self.channels[channel]['heating'] = heating
        self.disturbance = 0.0
