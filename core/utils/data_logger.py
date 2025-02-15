import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import json

class DataLogger:
    def __init__(self, num_channels: int = 16):
        """初始化数据记录器
        
        Args:
            num_channels: 通道数量
        """
        self.num_channels = num_channels
        self.data = {i: [] for i in range(num_channels)}  # 每个通道的数据列表
        
    def log_data(self, channel_data: Dict):
        """记录所有通道的数据"""
        print("\nDebug - 记录数据:")
        print(f"接收到的数据格式: {json.dumps(channel_data, indent=2)}")
        
        timestamp = channel_data.get("timestamp", datetime.now().isoformat())
        
        for ch in channel_data.get("channels", []):
            channel_id = ch.get("id")
            if channel_id is not None and 0 <= channel_id < self.num_channels:
                record = {
                    "temperature": ch.get("temperature", 25.0),
                    "target_temp": ch.get("pid_params", {}).get("target_temp", 25.0),
                    "kp": ch.get("pid_params", {}).get("kp", 1.0),
                    "ki": ch.get("pid_params", {}).get("ki", 0.1),
                    "kd": ch.get("pid_params", {}).get("kd", 0.05),
                    "heating": ch.get("heating", False),
                    "timestamp": timestamp
                }
                self.data[channel_id].append(record)
                print(f"已记录通道 {channel_id} 数据: {json.dumps(record, indent=2)}")
    
    def get_channel_data(self, channel: int, hours: Optional[float] = 1) -> pd.DataFrame:
        """获取指定通道的数据"""
        print(f"\nDebug - 获取通道 {channel} 数据:")
        print(f"数据存储状态: {list(self.data.keys())}")
        if channel in self.data:
            print(f"通道数据量: {len(self.data[channel])}")
            if self.data[channel]:
                print(f"最新数据: {json.dumps(self.data[channel][-1], indent=2)}")
        
        if not (0 <= channel < self.num_channels):
            print(f"通道ID {channel} 超出范围 [0, {self.num_channels-1}]")
            return pd.DataFrame()
            
        if not self.data[channel]:
            print(f"通道 {channel} 无数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(self.data[channel])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
        
        if hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            df = df[df.index >= cutoff]
            
        return df
    
    def get_channel_metrics(self, channel: int, hours: Optional[float] = None) -> Dict:
        """计算指定通道的性能指标
        
        Args:
            channel: 通道ID
            hours: 可选，计算最近多少小时的指标
            
        Returns:
            包含以下指标的字典：
            - rise_time: 上升时间（秒）
            - settling_time: 稳定时间（秒）
            - overshoot: 超调量（百分比）
            - steady_state_error: 稳态误差
            - temperature_std: 温度标准差
        """
        df = self.get_channel_data(channel, hours)
        if df.empty:
            return {
                "rise_time": None,
                "settling_time": None,
                "overshoot": None,
                "steady_state_error": None,
                "temperature_std": None
            }
            
        target_temp = df["target_temp"].iloc[-1]
        temp_data = df["temperature"]
        
        # 计算上升时间（从10%到90%）
        temp_range = temp_data.max() - temp_data.min()
        t_10 = temp_data.min() + 0.1 * temp_range
        t_90 = temp_data.min() + 0.9 * temp_range
        
        try:
            t_10_idx = temp_data[temp_data >= t_10].index[0]
            t_90_idx = temp_data[temp_data >= t_90].index[0]
            rise_time = (t_90_idx - t_10_idx).total_seconds()
        except IndexError:
            rise_time = None
            
        # 计算超调量
        max_temp = temp_data.max()
        overshoot = ((max_temp - target_temp) / target_temp) * 100 if target_temp != 0 else None
        
        # 计算稳定时间（温度在目标温度±2%范围内）
        tolerance = 0.02 * target_temp
        steady_mask = (temp_data >= target_temp - tolerance) & (temp_data <= target_temp + tolerance)
        try:
            settling_time = (steady_mask[steady_mask].index[0] - df.index[0]).total_seconds()
        except IndexError:
            settling_time = None
            
        # 计算稳态误差（最后10个点的平均值）
        steady_state_temp = temp_data.iloc[-10:].mean()
        steady_state_error = target_temp - steady_state_temp
        
        # 计算温度标准差
        temperature_std = temp_data.std()
        
        return {
            "rise_time": rise_time,
            "settling_time": settling_time,
            "overshoot": overshoot,
            "steady_state_error": steady_state_error,
            "temperature_std": temperature_std
        }
    
    def analyze_cooling_curve(self, channel: int, start_time: Optional[str] = None) -> Dict:
        """分析指定通道的冷却曲线
        
        Args:
            channel: 通道ID
            start_time: 可选，开始分析的时间点。如果不指定，使用最近一次停止加热的时间点。
            
        Returns:
            包含以下指标的字典：
            - cooling_rate: 冷却速率（°C/秒）
            - time_constant: 时间常数（秒）
            - final_temp: 最终温度
        """
        df = self.get_channel_data(channel)
        if df.empty:
            return {
                "cooling_rate": None,
                "time_constant": None,
                "final_temp": None
            }
            
        # 找到冷却开始点
        if start_time:
            start_idx = df.index[df.index >= start_time][0]
        else:
            heating_changes = df["heating"].diff()
            try:
                start_idx = df.index[heating_changes == -1][-1]  # 最后一次从加热变为不加热
            except IndexError:
                return {
                    "cooling_rate": None,
                    "time_constant": None,
                    "final_temp": None
                }
                
        cooling_data = df.loc[start_idx:]
        if len(cooling_data) < 2:
            return {
                "cooling_rate": None,
                "time_constant": None,
                "final_temp": None
            }
            
        # 计算冷却速率（前10个点的平均斜率）
        initial_cooling = cooling_data.iloc[:10]
        if len(initial_cooling) >= 2:
            time_diff = (initial_cooling.index[-1] - initial_cooling.index[0]).total_seconds()
            temp_diff = initial_cooling["temperature"].iloc[-1] - initial_cooling["temperature"].iloc[0]
            cooling_rate = temp_diff / time_diff
        else:
            cooling_rate = None
            
        # 计算时间常数（温度下降到初始值和最终值之差的63.2%处所用的时间）
        initial_temp = cooling_data["temperature"].iloc[0]
        final_temp = cooling_data["temperature"].iloc[-1]
        target_temp = initial_temp - 0.632 * (initial_temp - final_temp)
        
        try:
            tau_idx = cooling_data[cooling_data["temperature"] <= target_temp].index[0]
            time_constant = (tau_idx - start_idx).total_seconds()
        except IndexError:
            time_constant = None
            
        return {
            "cooling_rate": cooling_rate,
            "time_constant": time_constant,
            "final_temp": final_temp
        }
    
    def save_to_file(self, filename: str):
        """保存数据到文件
        
        Args:
            filename: 文件名，支持.json和.csv格式
        """
        if filename.endswith('.json'):
            with open(filename, 'w') as f:
                json.dump(self.data, f)
        elif filename.endswith('.csv'):
            all_data = []
            for channel, data in self.data.items():
                for record in data:
                    record['channel'] = channel
                    all_data.append(record)
            pd.DataFrame(all_data).to_csv(filename, index=False)
        else:
            raise ValueError("Unsupported file format. Use .json or .csv")
    
    def load_from_file(self, filename: str):
        """从文件加载数据
        
        Args:
            filename: 文件名，支持.json和.csv格式
        """
        if filename.endswith('.json'):
            with open(filename, 'r') as f:
                self.data = json.load(f)
        elif filename.endswith('.csv'):
            df = pd.read_csv(filename)
            self.data = {i: [] for i in range(self.num_channels)}
            for _, row in df.iterrows():
                channel = int(row['channel'])
                if 0 <= channel < self.num_channels:
                    record = row.to_dict()
                    del record['channel']
                    self.data[channel].append(record)
        else:
            raise ValueError("Unsupported file format. Use .json or .csv")
            
    def clear_channel_data(self, channel: int) -> bool:
        """清空指定通道的所有数据
        
        Args:
            channel: 通道ID
            
        Returns:
            bool: 如果清空成功返回True，如果通道ID无效返回False
        """
        if not (0 <= channel < self.num_channels):
            print(f"通道ID {channel} 超出范围 [0, {self.num_channels-1}]")
            return False
            
        self.data[channel] = []
        print(f"已清空通道 {channel} 的所有数据")
        return True
        
    def clear_all_data(self):
        """清空所有通道的所有数据"""
        self.data = {i: [] for i in range(self.num_channels)}
        print("已清空所有通道的数据")
