from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi_app.utils.serial_comm import SerialManager, list_serial_ports
from fastapi_app.utils.data_store import DBlogger
from core.agent.pid_agent import PIDAgent
import pandas as pd
import json

router = APIRouter()

# 常用波特率列表
COMMON_BAUDRATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]

# 全局变量
serial_manager: Optional[SerialManager] = None
db_data_logger: Optional[DBlogger] = None
pid_agent: Optional[PIDAgent] = None

class PIDParams(BaseModel):
    kp: float
    ki: float
    kd: float
    target_temp: float
    control_period: Optional[int] = 100  # ms
    max_duty: Optional[int] = 80  # %

class ChannelState(BaseModel):
    id: int
    temperature: float
    pid_params: PIDParams
    heating: bool

class SystemState(BaseModel):
    timestamp: str
    channels: List[ChannelState]

class ChannelConfig(BaseModel):
    port: str  # 串口名称
    baudrate: int  # 波特率
    num_channels: int = 16  # 通道数
    use_mock: bool = False  # 是否使用虚拟串口

@router.post("/disconnect")
def disconnect_device():
    print("\n=== API: /disconnect START ===\n")
    try:
        global serial_manager, pid_agent, db_data_logger
        if serial_manager is None:
            print("DEBUG - API: No device manager")
            print("\n=== API: /disconnect END (no manager) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Device not connected"
            )
        
        if serial_manager.disconnect():
            print("DEBUG - API: Device disconnected successfully")
            serial_manager = None
            pid_agent = None
            db_data_logger = None
            print("\n=== API: /disconnect END ===\n")
            return {"status": "disconnected"}
        else:
            print("DEBUG - API: Failed to disconnect device")
            print("\n=== API: /disconnect END (failed) ===\n")
            raise HTTPException(
                status_code=500,
                detail="Failed to disconnect device"
            )
    except Exception as e:
        print(f"DEBUG - API: Disconnect error: {str(e)}")
        print("\n=== API: /disconnect END (with error) ===\n")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect device: {str(e)}"
        )

@router.get("/ports")
async def get_serial_ports():
    """获取可用的串口列表
    
    Returns:
        Dict: {
            "ports": [
                {
                    "port": 串口名称,
                    "description": 串口描述
                }
            ],
            "baudrates": [支持的波特率列表],
            "virtual_port": 虚拟串口名称
        }
    """
    try:
        # 获取系统串口列表
        ports = list_serial_ports()
        
        # 添加虚拟串口选项
        virtual_port = "VIRTUAL"
        
        return {
            "ports": ports,
            "baudrates": COMMON_BAUDRATES,
            "virtual_port": virtual_port
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get serial ports: {str(e)}"
        )

@router.post("/connect")
async def connect_device(config: ChannelConfig):
    print("\n=== API: /connect START ===\n")
    try:
        print(f"DEBUG - API: Connecting device with config: {config}")
        global serial_manager, db_data_logger, pid_agent
        
        # 初始化或重新初始化设备管理器
        print("DEBUG - API: Creating SerialManager")
        new_serial_manager = SerialManager(
            port=config.port,
            baudrate=config.baudrate,
            num_channels=config.num_channels,
            use_mock=config.use_mock
        )
        
        # 先尝试连接
        print("DEBUG - API: Attempting to connect")
        if not new_serial_manager.connect():
            print("DEBUG - API: Connection failed")
            print("\n=== API: /connect END (connection failed) ===\n")
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to device"
            )
        
        # 连接成功后初始化其他组件
        print("DEBUG - API: Creating DBlogger")
        new_db_logger = DBlogger(num_channels=config.num_channels)
        
        print("DEBUG - API: Creating PID Agent")
        new_pid_agent = PIDAgent(num_channels=config.num_channels)
        
        # 全部初始化成功后，更新全局变量
        serial_manager = new_serial_manager
        db_data_logger = new_db_logger
        pid_agent = new_pid_agent
            
        print("DEBUG - API: Device connected successfully")
        result = {
            "status": "connected",
            "port": config.port,
            "baudrate": config.baudrate,
            "use_mock": config.use_mock,
            "num_channels": config.num_channels
        }
        print(f"DEBUG - API: Returning result: {result}")
        print("\n=== API: /connect END ===\n")
        return result
            
        print("DEBUG - API: Failed to connect")
        print("\n=== API: /connect END (with error) ===\n")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to device"
        )
    except Exception as e:
        import traceback
        print(f"DEBUG - API: Connection error: {str(e)}")
        print(f"DEBUG - API: Traceback: {traceback.format_exc()}")
        print("\n=== API: /connect END (with exception) ===\n")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to device: {str(e)}"
        )

@router.get("/channel/{channel_id}/history")
async def get_channel_history(channel_id: int, hours: int = 24):
    try:
        if not serial_manager or not serial_manager.is_connected():
            raise HTTPException(
                status_code=400,
                detail="Device not connected. Please connect first."
            )
        
        if channel_id >= serial_manager.num_channels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid channel ID. Must be between 0 and {serial_manager.num_channels - 1}"
            )
        
        history = db_data_logger.get_history(hours=hours, channel_id=channel_id)
        return history.to_dict(orient='records')
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get channel history: {str(e)}"
        )

@router.get("/status")
async def get_device_status():
    print("\n=== API: /status START ===\n")
    try:
        if not serial_manager:
            print("DEBUG - API: serial_manager is None")
            print("\n=== API: /status END (no manager) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Device not connected. Please connect first."
            )
        
        if not serial_manager.is_connected():
            print("DEBUG - API: device not connected")
            print("\n=== API: /status END (not connected) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Device not connected. Please connect first."
            )
        
        print("DEBUG - API: Getting device status")
        status = serial_manager.get_status()
        print(f"DEBUG - API: Got status: {status}")
        
        # 记录数据
        if db_data_logger is not None:
            print("DEBUG - API: Logging data to db_data_logger")
            db_data_logger.log_data(status.get('channels', []))
            
        # 同时记录到PID Agent
        if pid_agent is not None:
            print("DEBUG - API: Logging data to PID Agent")
            pid_agent.log_data(status)
        
        print("\n=== API: /status END ===\n")
        return status
    except Exception as e:
        import traceback
        print(f"DEBUG - API: Status error: {str(e)}")
        print(f"DEBUG - API: Traceback: {traceback.format_exc()}")
        print("\n=== API: /status END (with exception) ===\n")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse device data: {str(e)}"
        )

@router.post("/channel/{channel_id}/pid")
async def update_channel_pid(channel_id: int, params: PIDParams):
    try:
        command = f"PID:{channel_id}:{params.kp},{params.ki},{params.kd},{params.target_temp},{params.control_period},{params.max_duty}"
        if serial_manager.send_command(command):
            return {"status": "success", "message": f"Channel {channel_id} PID parameters updated"}
        raise HTTPException(status_code=500, detail="Failed to send command")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update PID parameters: {str(e)}")

class HeatingControl(BaseModel):
    heating: bool

@router.post("/channel/{channel_id}/control")
async def control_channel(channel_id: int, control: HeatingControl):
    print("\n=== API: /channel/control START ===\n")
    print(f"DEBUG - API: Controlling channel {channel_id}, heating={control.heating}")
    try:
        if not serial_manager:
            print("DEBUG - API: serial_manager is None")
            print("\n=== API: /channel/control END (no manager) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Device not connected. Please connect first."
            )
        
        if not serial_manager.is_connected():
            print("DEBUG - API: device not connected")
            print("\n=== API: /channel/control END (not connected) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Device not connected. Please connect first."
            )
        
        success = False
        if control.heating:
            print(f"DEBUG - API: Starting heating for channel {channel_id}")
            success = serial_manager.start_heating(channel_id)
            print(f"DEBUG - API: Start heating result: {success}")
        else:
            print(f"DEBUG - API: Stopping heating for channel {channel_id}")
            success = serial_manager.stop_heating(channel_id)
            print(f"DEBUG - API: Stop heating result: {success}")
            
        if success:
            print(f"DEBUG - API: Successfully {'started' if control.heating else 'stopped'} heating for channel {channel_id}")
            print("\n=== API: /channel/control END ===\n")
            return {"status": "success", "message": f"Channel {channel_id} heating {'started' if control.heating else 'stopped'}"}
            
        print(f"DEBUG - API: Failed to {'start' if control.heating else 'stop'} heating for channel {channel_id}")
        print("\n=== API: /channel/control END (command failed) ===\n")
        raise HTTPException(status_code=500, detail="Failed to send command")
    except Exception as e:
        import traceback
        print(f"DEBUG - API: Error controlling channel: {str(e)}")
        print(f"DEBUG - API: Traceback: {traceback.format_exc()}")
        print("\n=== API: /channel/control END (with exception) ===\n")
        raise HTTPException(status_code=500, detail=f"Failed to control channel: {str(e)}")

@router.get("/history")
async def get_history(hours: int = 24):
    try:
        if not db_data_logger:
            raise HTTPException(
                status_code=400,
                detail="Data logger not initialized. Please connect first."
            )
            
        history = db_data_logger.get_history(hours=hours)
        print(f"DEBUG - API: Got {len(history)} history records")
        return history.to_dict('records')
    except Exception as e:
        print(f"DEBUG - API: Failed to fetch history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@router.delete("/channel/{channel_id}/data")
async def clear_channel_data(channel_id: int):
    print("\n=== API: /channel/data/clear START ===\n")
    try:
        if not db_data_logger:
            print("DEBUG - API: db_data_logger is None")
            print("\n=== API: /channel/data/clear END (no logger) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Data logger not initialized. Please connect first."
            )
            
        print(f"DEBUG - API: Clearing data for channel {channel_id}")
        # 同时clear到PID Agent data
        if pid_agent is not None:
            print("DEBUG - API: pid_agent.clear_channel_data")
            pid_agent.clear_channel_data(channel_id)
        if db_data_logger.clear_channel_data(channel_id):
            print(f"DEBUG - API: Successfully cleared data for channel {channel_id}")
            print("\n=== API: /channel/data/clear END ===\n")
            return {"status": "success", "message": f"Cleared data for channel {channel_id}"}
        else:
            print(f"DEBUG - API: Invalid channel ID {channel_id}")
            print("\n=== API: /channel/data/clear END (invalid channel) ===\n")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid channel ID {channel_id}"
            )
            
    except Exception as e:
        import traceback
        print(f"DEBUG - API: Error clearing channel data: {str(e)}")
        print(f"DEBUG - API: Traceback: {traceback.format_exc()}")
        print("\n=== API: /channel/data/clear END (with exception) ===\n")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear channel data: {str(e)}"
        )

@router.delete("/data")
async def clear_all_data():
    print("\n=== API: /data/clear START ===\n")
    try:
        if not db_data_logger:
            print("DEBUG - API: db_data_logger is None")
            print("\n=== API: /data/clear END (no logger) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Data logger not initialized. Please connect first."
            )
            
        print("DEBUG - API: Clearing all channel data")
        db_data_logger.clear_all_data()
         # 同时clear到PID Agent data
        if pid_agent is not None:
            print("DEBUG - API: pid_agent.clear_all_data")
            pid_agent.clear_all_data()
        print("DEBUG - API: Successfully cleared all channel data")
        print("\n=== API: /data/clear END ===\n")
        return {"status": "success", "message": "Cleared all channel data"}
            
    except Exception as e:
        import traceback
        print(f"DEBUG - API: Error clearing all data: {str(e)}")
        print(f"DEBUG - API: Traceback: {traceback.format_exc()}")
        print("\n=== API: /data/clear END (with exception) ===\n")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear all data: {str(e)}"
        )
