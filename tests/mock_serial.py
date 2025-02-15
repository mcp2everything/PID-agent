import json
from typing import Optional, Dict
from .mock_pid_system import MockPIDSystem

class MockSerial:
    def __init__(self, num_channels: int = 16):
        self.is_open = False
        self.pid_system = MockPIDSystem(num_channels=num_channels)
        
    def open(self):
        """模拟打开串口"""
        self.is_open = True
        
    def close(self):
        """模拟关闭串口"""
        self.is_open = False
        
    def readline(self) -> bytes:
        """模拟读取一行数据"""
        if not self.is_open:
            return b''
            
        state = self.pid_system.get_current_state()
        return (json.dumps(state) + '\n').encode()
        
    def write(self, data: bytes) -> int:
        """模拟写入数据（更新PID参数或控制加热）"""
        if not self.is_open:
            return 0
            
        try:
            command = data.decode().strip()
            
            # 解析PID参数命令：PID:<channel>,<kp>,<ki>,<kd>,<target_temp>
            if command.startswith('PID:'):
                params = command.split(':')[1].split(',')
                channel = int(params[0])
                kp, ki, kd, target = map(float, params[1:])
                self.pid_system.update_params(channel, kp, ki, kd, target)
                return len(data)
            
            # 解析加热控制命令：HEAT_ON:<channel> 或 HEAT_OFF:<channel>
            elif command.startswith(('HEAT_ON:', 'HEAT_OFF:')):
                action, channel = command.split(':')
                channel = int(channel)
                heating = action == 'HEAT_ON'
                self.pid_system.set_heating(channel, heating)
                return len(data)
                
        except Exception as e:
            print(f"Error processing command: {str(e)}")
        return 0
        
    def add_disturbance(self, magnitude: float = 1.0):
        """添加外部干扰"""
        self.pid_system.add_disturbance(magnitude)
        
    def reset(self):
        """重置系统状态"""
        self.pid_system.reset()
