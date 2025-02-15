import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class DataLogger:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        self.current_file = None
        self.data = []
    
    def start_new_session(self):
        """开始新的数据记录会话"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file = os.path.join(self.data_dir, f"session_{timestamp}.json")
        self.data = []
    
    def log_data(self, temperature: float, pid_params: Dict, timestamp: Optional[str] = None):
        """记录一条数据"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
            
        data_point = {
            "temperature": temperature,
            "pid_params": pid_params,
            "timestamp": timestamp
        }
        self.data.append(data_point)
        
        # 实时保存到文件
        if self.current_file:
            with open(self.current_file, "w") as f:
                json.dump(self.data, f, indent=2)
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """获取历史数据"""
        if limit is None:
            return self.data
        return self.data[-limit:]
    
    def get_latest(self) -> Optional[Dict]:
        """获取最新的数据点"""
        if not self.data:
            return None
        return self.data[-1]
    
    def analyze_curve(self, target_temp: float) -> Dict:
        """分析温度曲线特征"""
        if not self.data:
            return {
                "rise_time": None,
                "overshoot": None,
                "steady_state_error": None,
                "settling_time": None
            }
        
        temperatures = [d["temperature"] for d in self.data]
        
        # 计算上升时间（从开始到首次达到目标温度的时间）
        rise_time = None
        for i, temp in enumerate(temperatures):
            if temp >= target_temp:
                rise_time = i
                break
        
        # 计算超调量
        max_temp = max(temperatures)
        overshoot = ((max_temp - target_temp) / target_temp) * 100 if max_temp > target_temp else 0
        
        # 计算稳态误差（使用最后10个点的平均值）
        steady_state_temp = sum(temperatures[-10:]) / len(temperatures[-10:]) if len(temperatures) >= 10 else temperatures[-1]
        steady_state_error = abs(steady_state_temp - target_temp)
        
        # 计算整定时间（温度保持在目标温度±5%范围内的时间）
        settling_time = None
        error_band = target_temp * 0.05
        for i, temp in enumerate(temperatures):
            if abs(temp - target_temp) <= error_band:
                settling_time = i
                # 检查后续是否都在范围内
                all_settled = True
                for t in temperatures[i:]:
                    if abs(t - target_temp) > error_band:
                        all_settled = False
                        break
                if all_settled:
                    break
        
        return {
            "rise_time": rise_time,
            "overshoot": overshoot,
            "steady_state_error": steady_state_error,
            "settling_time": settling_time
        }
