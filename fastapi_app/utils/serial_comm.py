# fastapi_app/utils/serial_comm.py
import serial
import serial.tools.list_ports
import json
import random
from datetime import datetime
from typing import Optional, Union, Dict, List
from fastapi_app.config import settings

def list_serial_ports() -> List[Dict[str, str]]:
    """获取系统串口列表
    
    Returns:
        List[Dict[str, str]]: [
            {
                "port": 串口名称,
                "description": 串口描述
            }
        ]
    """
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append({
            "port": port.device,
            "description": port.description
        })
    return ports

# 实现一个模拟串口类
class MockSerial:
    def __init__(self, num_channels: int = 16):
        print("\n=== MockSerial: init START ===\n")
        self.is_open = False
        self.channels = {}
        self.last_update = datetime.now()
        self.update_interval = 0.1  # 100ms
        self.num_channels = num_channels
        
        # 初始化所有通道
        print(f"DEBUG - MockSerial: Initializing {num_channels} channels")
        for channel_id in range(num_channels):
            self.channels[channel_id] = {
                'temperature': 25.0,
                'target_temp': 25.0,
                'kp': 1.0,
                'ki': 0.1,
                'kd': 0.05,
                'control_period': 100,
                'max_duty': 80,
                'heating': False
            }
            print(f"DEBUG - MockSerial: Initialized channel {channel_id}: {self.channels[channel_id]}")
        print("\n=== MockSerial: init END ===\n")
        
    def open(self):
        print("\n=== MockSerial: open START ===\n")
        self.is_open = True
        print("DEBUG - MockSerial: Device opened")
        print("\n=== MockSerial: open END ===\n")
    
    def close(self):
        print("\n=== MockSerial: close START ===\n")
        self.is_open = False
        print("DEBUG - MockSerial: Device closed")
        print("\n=== MockSerial: close END ===\n")
        
    def readline(self) -> bytes:
        print("\n=== MockSerial: readline START ===\n")
        # 模拟真实通信延迟
        now = datetime.now()
        if (now - self.last_update).total_seconds() < self.update_interval:
            print("DEBUG - MockSerial: Too soon to update")
            print("\n=== MockSerial: readline END (too soon) ===\n")
            return b''
        
        self.last_update = now
        print(f"DEBUG - MockSerial: Current channels state: {self.channels}")
        
        # 为每个通道生成数据
        channels = []
        for channel_id in range(self.num_channels):
            print(f"DEBUG - MockSerial: Processing channel {channel_id}")
            
            # 现在通道已经在 __init__ 中初始化了，这里直接使用
            channel = self.channels[channel_id]
            print(f"DEBUG - MockSerial: Channel {channel_id} current state: {channel}")
            
            # 模拟温度变化
            if channel['heating']:
                print(f"DEBUG - MockSerial: Channel {channel_id} is heating, increasing temperature")
                # 在加热状态下温度会缓慢上升
                channel['temperature'] += 0.05
                print(f"DEBUG - MockSerial: Channel {channel_id} temperature increased to {channel['temperature']}")
            else:
                if channel['temperature'] > 25.0:
                    print(f"DEBUG - MockSerial: Channel {channel_id} is cooling, decreasing temperature")
                    # 在非加热状态下温度会缓慢下降
                    channel['temperature'] -= 0.02
                    print(f"DEBUG - MockSerial: Channel {channel_id} temperature decreased to {channel['temperature']}")
            
            channel_data = {
                'id': channel_id,
                'temperature': float(channel['temperature']),
                'pid_params': {
                    'kp': float(channel['kp']),
                    'ki': float(channel['ki']),
                    'kd': float(channel['kd']),
                    'target_temp': float(channel['target_temp']),
                    'control_period': int(channel['control_period']),
                    'max_duty': int(channel['max_duty'])
                },
                'heating': bool(channel['heating'])
            }
            print(f"DEBUG - MockSerial: Channel {channel_id} data to return: {channel_data}")
            channels.append(channel_data)
        
        data = {
            'timestamp': now.strftime('%Y-%m-%dT%H:%M:%S'),
            'channels': channels,
            'status': 'running'
        }
        
        print(f"DEBUG - MockSerial: Preparing data to return: {data}")
        
        # 确保返回的是字艶串
        try:
            encoded_data = json.dumps(data).encode() + b'\n'
            print(f"DEBUG - MockSerial: Encoded data: {encoded_data}")
            print("\n=== MockSerial: readline END ===\n")
            return encoded_data
        except Exception as e:
            print(f"Error encoding data: {str(e)}")
            return b''
    
    def write(self, data: bytes) -> int:
        print("\n=== MockSerial: write START ===\n")
        try:
            cmd = data.decode().strip()
            print(f"DEBUG - MockSerial: Received command: {cmd}")
            parts = cmd.split(':')
            
            if len(parts) < 2:
                print("DEBUG - MockSerial: Invalid command format - not enough parts")
                print("\n=== MockSerial: write END (invalid format) ===\n")
                return len(data)
            
            cmd_type = parts[0]
            channel_id = int(parts[1])
            print(f"DEBUG - MockSerial: Command type={cmd_type}, channel={channel_id}")
            
            if channel_id not in self.channels:
                print(f"DEBUG - MockSerial: Creating new channel {channel_id}")
                self.channels[channel_id] = {
                    'temperature': 25.0,
                    'target_temp': 25.0,
                    'kp': 1.0,
                    'ki': 0.1,
                    'kd': 0.05,
                    'control_period': 100,
                    'max_duty': 80,
                    'heating': False
                }
            
            if cmd_type == 'HEAT':
                # HEAT:channel_id:1/0
                if len(parts) >= 3:
                    try:
                        print(f"DEBUG - MockSerial: Processing HEAT command for channel {channel_id}")
                        print(f"DEBUG - MockSerial: Raw heating state value: {parts[2]}")
                        
                        # 解析加热状态
                        heating_state = bool(int(parts[2]))
                        print(f"DEBUG - MockSerial: Parsed heating state: {heating_state}")
                        
                        # 检查通道当前状态
                        print(f"DEBUG - MockSerial: Channel {channel_id} current state: {self.channels[channel_id]}")
                        print(f"DEBUG - MockSerial: Current heating state: {self.channels[channel_id].get('heating', False)}")
                        
                        # 更新加热状态
                        self.channels[channel_id]['heating'] = heating_state
                        print(f"DEBUG - MockSerial: Updated heating state: {self.channels[channel_id]['heating']}")
                        
                        # 更新温度
                        if heating_state:
                            print(f"DEBUG - MockSerial: Channel {channel_id} starting to heat")
                            self.channels[channel_id]['temperature'] += 0.1
                        elif self.channels[channel_id]['temperature'] > 25.0:
                            print(f"DEBUG - MockSerial: Channel {channel_id} starting to cool")
                            self.channels[channel_id]['temperature'] -= 0.05
                        
                        print(f"DEBUG - MockSerial: Final channel state: {self.channels[channel_id]}")
                        print("\n=== MockSerial: write END (heating updated) ===\n")
                        return len(data)  # 处理完 HEAT 命令后直接返回，不再处理其他命令
                        
                    except ValueError as e:
                        print(f"DEBUG - MockSerial: Invalid heating state value: {parts[2]}")
                        print(f"DEBUG - MockSerial: Error details: {str(e)}")
                        print("\n=== MockSerial: write END (invalid heating state) ===\n")
                        return len(data)  # 发生错误也直接返回
                else:
                    print("DEBUG - MockSerial: Missing heating state value")
                    print(f"DEBUG - MockSerial: Command parts: {parts}")
                    print("\n=== MockSerial: write END (missing heating state) ===\n")
                    return len(data)  # 参数不足也直接返回
            
            elif cmd_type == 'PID':
                # PID:channel_id:kp,ki,kd,target_temp,control_period,max_duty
                try:
                    params = parts[2].split(',')
                    print(f"DEBUG - MockSerial: Channel {channel_id} state before PID update: {self.channels[channel_id]}")
                    self.channels[channel_id].update({
                        'kp': float(params[0]),
                        'ki': float(params[1]),
                        'kd': float(params[2]),
                        'target_temp': float(params[3]),
                        'control_period': int(params[4]),
                        'max_duty': int(params[5])
                    })
                    print(f"DEBUG - MockSerial: Channel {channel_id} state after PID update: {self.channels[channel_id]}")
                    print("\n=== MockSerial: write END (PID updated) ===\n")
                    return len(data)
                except (ValueError, IndexError) as e:
                    print(f"DEBUG - MockSerial: Invalid PID parameters: {str(e)}")
                    print("\n=== MockSerial: write END (invalid PID params) ===\n")
                    return len(data)
            else:
                print(f"DEBUG - MockSerial: Unknown command type: {cmd_type}")
                print("\n=== MockSerial: write END (unknown command) ===\n")
                return len(data)
                
        except Exception as e:
            import traceback
            print(f"DEBUG - MockSerial: Error processing command: {str(e)}")
            print(f"DEBUG - MockSerial: Traceback: {traceback.format_exc()}")
            print("\n=== MockSerial: write END (with error) ===\n")
            return len(data)
    
    def add_disturbance(self, magnitude: float = 1.0):
        for channel in self.channels.values():
            channel['temperature'] += random.uniform(-magnitude, magnitude)
    
    def reset(self):
        print("\n=== MockSerial: reset START ===\n")
        print("DEBUG - MockSerial: Resetting all channels")
        # 重新初始化所有通道
        for channel_id in range(self.num_channels):
            self.channels[channel_id] = {
                'temperature': 25.0,
                'target_temp': 25.0,
                'kp': 1.0,
                'ki': 0.1,
                'kd': 0.05,
                'control_period': 100,
                'max_duty': 80,
                'heating': False
                }
        print(f"DEBUG - MockSerial: Reset channel {channel_id}: {self.channels[channel_id]}")
        print("\n=== MockSerial: reset END ===\n")

class SerialManager:
    def __init__(self, port: str, baudrate: int, num_channels: int = 16, use_mock: bool = False):
        self.port = port
        self.baud = baudrate
        self.use_mock = use_mock or port == "VIRTUAL"
        self.num_channels = num_channels
        self.connection: Optional[Union[serial.Serial, MockSerial]] = None
        self.last_data = None
    
    def is_connected(self) -> bool:
        return self.connection is not None and self.connection.is_open
        
    def disconnect(self) -> bool:
        print("\n=== SerialManager: disconnect START ===\n")
        try:
            if self.connection and self.connection.is_open:
                print("DEBUG - SerialManager: Closing connection")
                self.connection.close()
                self.connection = None
                print("DEBUG - SerialManager: Connection closed successfully")
                print("\n=== SerialManager: disconnect END ===\n")
                return True
            else:
                print("DEBUG - SerialManager: No connection to close")
                print("\n=== SerialManager: disconnect END (no connection) ===\n")
                return False
        except Exception as e:
            print(f"DEBUG - SerialManager: Failed to close connection: {str(e)}")
            import traceback
            print(f"DEBUG - SerialManager: Traceback: {traceback.format_exc()}")
            print("\n=== SerialManager: disconnect END (with error) ===\n")
            return False
    
    def get_status(self) -> dict:
        print("\n=== SerialManager: get_status START ===\n")
        if not self.is_connected():
            print("DEBUG - SerialManager: Device not connected")
            print("\n=== SerialManager: get_status END (not connected) ===\n")
            raise Exception("Device not connected")
            
        try:
            # 只读取一次数据
            print("DEBUG - SerialManager: Reading data from connection")
            line = self.connection.readline()
            print(f"DEBUG - SerialManager: Read data: {line}")
            
            if line:
                try:
                    if isinstance(line, bytes):
                        print("DEBUG - SerialManager: Decoding bytes data")
                        data = json.loads(line.decode())
                    elif isinstance(line, dict):
                        print("DEBUG - SerialManager: Using dict data directly")
                        data = line
                    else:
                        print("DEBUG - SerialManager: Converting to string and decoding")
                        data = json.loads(str(line))
                        
                    if data:
                        print(f"DEBUG - SerialManager: Got valid data: {data}")
                        self.last_data = data
                        print("\n=== SerialManager: get_status END (with new data) ===\n")
                        return self.last_data
                except json.JSONDecodeError as e:
                    print(f"DEBUG - SerialManager: JSON decode error: {str(e)}")
                    print(f"DEBUG - SerialManager: Failed to decode: {line}")
                except Exception as e:
                    print(f"DEBUG - SerialManager: Error parsing data: {str(e)}")
                    import traceback
                    print(f"DEBUG - SerialManager: Traceback: {traceback.format_exc()}")
            else:
                print("DEBUG - SerialManager: No data received from device")
            
            # 如果没有数据，使用上次的数据或创建空数据
            if self.last_data is not None:
                print("DEBUG - SerialManager: Using last known data")
                print(f"DEBUG - SerialManager: Last data: {self.last_data}")
                print("\n=== SerialManager: get_status END (using last data) ===\n")
                return self.last_data
            
            print("DEBUG - SerialManager: Creating empty data")
            self.last_data = {
                'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'channels': []
            }
            print(f"DEBUG - SerialManager: Empty data: {self.last_data}")
            print("\n=== SerialManager: get_status END (with empty data) ===\n")
            return self.last_data
            
        except Exception as e:
            raise Exception(f"Failed to read device status: {str(e)}")

    def send_command(self, command: str) -> bool:
        """发送命令到设备
        
        Args:
            command: 要发送的命令字符串
            
        Returns:
            bool: 命令是否发送成功
        """
        print("\n=== SerialManager: send_command START ===\n")
        try:
            if not self.is_connected():
                print("DEBUG - SerialManager: Device not connected")
                print("\n=== SerialManager: send_command END (not connected) ===\n")
                raise Exception("Device not connected")
                
            print(f"DEBUG - SerialManager: Sending command: {command}")
            self.connection.write(command.encode() + b'\n')
            print("DEBUG - SerialManager: Command sent successfully")
            print("\n=== SerialManager: send_command END ===\n")
            return True
        except Exception as e:
            import traceback
            print(f"DEBUG - SerialManager: Failed to send command: {str(e)}")
            print(f"DEBUG - SerialManager: Traceback: {traceback.format_exc()}")
            print("\n=== SerialManager: send_command END (with error) ===\n")
            return False
    
    def connect(self) -> bool:
        print(f"DEBUG - SerialManager: Connecting with use_mock={self.use_mock}")
        try:
            # 如果已经有连接，先关闭
            if self.connection and self.connection.is_open:
                print("DEBUG - SerialManager: Closing existing connection")
                self.connection.close()

            if self.use_mock:
                print(f"DEBUG - SerialManager: Creating MockSerial connection with {self.num_channels} channels")
                self.connection = MockSerial(num_channels=self.num_channels)
                self.connection.open()
            else:
                print(f"DEBUG - SerialManager: Creating real serial connection on port {self.port}")
                self.connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baud,
                    timeout=1
                )
            
            is_open = self.connection.is_open
            print(f"DEBUG - SerialManager: Connection {'opened' if is_open else 'failed to open'}")
            return is_open
        except Exception as e:
            print(f"DEBUG - SerialManager: Connection error: {str(e)}")
            import traceback
            print(f"DEBUG - SerialManager: Traceback: {traceback.format_exc()}")
            return False

    def read_data(self) -> Dict:
        """读取所有通道的数据"""
        return self.get_status()
    
    def _empty_data(self) -> Dict:
        """创建空数据结构"""
        return {
            "channels": [
                {
                    "id": i,
                    "temperature": 25.0,
                    "pid_params": {
                        "kp": 1.0,
                        "ki": 0.1,
                        "kd": 0.05,
                        "target_temp": 25.0,
                        "control_period": 100,
                        "max_duty": 100
                    },
                    "heating": False
                } for i in range(self.num_channels)
            ],
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }

    def send_command(self, cmd: str) -> bool:
        """发送通用命令"""
        print("\n=== SerialManager: send_command START ===\n")
        print(f"DEBUG - SerialManager: Sending command: {cmd}")
        if not self.connection:
            print("DEBUG - SerialManager: No connection available")
            print("\n=== SerialManager: send_command END (no connection) ===\n")
            return False
        
        if not self.connection.is_open:
            print("DEBUG - SerialManager: Connection is not open")
            print("\n=== SerialManager: send_command END (not open) ===\n")
            return False
        
        try:
            print("DEBUG - SerialManager: Writing command to connection")
            self.connection.write(f"{cmd}\n".encode())
            print("DEBUG - SerialManager: Command written successfully")
            print("\n=== SerialManager: send_command END ===\n")
            return True
        except Exception as e:
            print(f"DEBUG - SerialManager: Failed to send command: {str(e)}")
            import traceback
            print(f"DEBUG - SerialManager: Traceback: {traceback.format_exc()}")
            print("\n=== SerialManager: send_command END (with error) ===\n")
            return False
    
    def start_heating(self, channel: int) -> bool:
        """开始指定通道的加热"""
        print("\n=== SerialManager: 开始加热 START ===\n")
        print(f"DEBUG - SerialManager: Starting heating for channel {channel}")
        if 0 <= channel < self.num_channels:
            result = self.send_command(f"HEAT:{channel}:1")
            print(f"DEBUG - SerialManager: Start heating result: {result}")
            print("\n=== SerialManager: 开始加热 END ===\n")
            return result
        print("DEBUG - SerialManager: Invalid channel number")
        print("\n=== SerialManager: start_heating END (invalid channel) ===\n")
        return False
    
    def stop_heating(self, channel: int) -> bool:
        """停止指定通道的加热"""
        print("\n=== SerialManager: 停止加热 START ===\n")
        print(f"DEBUG - SerialManager: Stopping heating for channel {channel}")
        if 0 <= channel < self.num_channels:
            result = self.send_command(f"HEAT:{channel}:0")
            print(f"DEBUG - SerialManager: Stop heating result: {result}")
            print("\n=== SerialManager: 停止加热 END ===\n")
            return result
        print("DEBUG - SerialManager: Invalid channel number")
        print("\n=== SerialManager: stop_heating END (invalid channel) ===\n")
        return False
    
    def set_pid_params(self, channel: int, kp: float, ki: float, kd: float, target_temp: float,
                      control_period: int = 100, max_duty: int = 100) -> bool:
        """设置指定通道的PID参数
        
        Args:
            channel: 通道ID
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
            target_temp: 目标温度
            control_period: PID控制周期（毫秒），范围[10, 1000]
            max_duty: 最大占空比（%），范围[0, 100]
        """
        if 0 <= channel < self.num_channels:
            # 验证参数范围
            control_period = max(10, min(1000, control_period))
            max_duty = max(0, min(100, max_duty))
            return self.send_command(f"PID:{channel},{kp},{ki},{kd},{target_temp},{control_period},{max_duty}")
        return False
    
    def add_disturbance(self, channel: int, magnitude: float = 1.0):
        """为指定通道添加外部干扰（仅在模拟模式下可用）"""
        if self.use_mock and self.connection and 0 <= channel < self.num_channels:
            self.connection.add_disturbance(channel, magnitude)
    
    def reset(self, channel: Optional[int] = None):
        """重置系统状态（仅在模拟模式下可用）
        
        Args:
            channel: 如果指定，只重置该通道；否则重置所有通道
        """
        if self.use_mock and self.connection:
            if channel is not None and 0 <= channel < self.num_channels:
                self.connection.reset(channel)
            else:
                self.connection.reset()