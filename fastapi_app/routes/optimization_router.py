from fastapi import APIRouter, HTTPException
from typing import Dict, Optional, List
from pydantic import BaseModel
from datetime import datetime
import fastapi_app.routes.device_router as device_router

router = APIRouter()

class OptimizationRequest(BaseModel):
    channel_id: int
    hours: Optional[float] = 1.0

@router.post("/channel/{channel_id}/optimize")
async def optimize_channel(channel_id: int, hours: Optional[float] = 1.0):
    print("\n=== API: /optimization/channel/optimize START ===\n")
    try:
        # 检查PID Agent是否已初始化
        if device_router.pid_agent is None:
            print("DEBUG - API: PID Agent not initialized")
            print("\n=== API: /optimization/channel/optimize END (no agent) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Device not connected. Please connect first."
            )
            
        # 获取当前状态并记录数据
        print("DEBUG - API: Getting current device status")
        if not device_router.serial_manager or not device_router.serial_manager.is_connected():
            print("DEBUG - API: Device not connected")
            print("\n=== API: /optimization/channel/optimize END (not connected) ===\n")
            raise HTTPException(
                status_code=400,
                detail="Device not connected. Please connect first."
            )
        
        # 分析指定通道
        print(f"DEBUG - API: Analyzing channel {channel_id}")
        analysis = device_router.pid_agent.analyze_channel(channel_id, hours)
        print(f"DEBUG - API: Analysis result: {analysis}")
        print("\n=== API: /optimization/channel/optimize END ===\n")
        return analysis
        
    except Exception as e:
        import traceback
        print(f"DEBUG - API: Optimization error: {str(e)}")
        print(f"DEBUG - API: Traceback: {traceback.format_exc()}")
        print("\n=== API: /optimization/channel/optimize END (with error) ===\n")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze channel {channel_id}: {str(e)}"
        )

@router.post("/channels/optimize")
async def optimize_all_channels(hours: Optional[float] = 1.0):
    print("\n=== API: /optimization/channels/optimize START ===\n")
    try:
        global pid_agent
        
        # 如果还没有初始化 PID Agent，初始化它
        if pid_agent is None:
            print("DEBUG - API: Initializing PID Agent")
            from fastapi_app.routes.device_router import serial_manager
            if not serial_manager or not serial_manager.is_connected():
                print("DEBUG - API: Device not connected")
                print("\n=== API: /optimization/channels/optimize END (not connected) ===\n")
                raise HTTPException(
                    status_code=400,
                    detail="Device not connected. Please connect first."
                )
            pid_agent = PIDAgent(num_channels=serial_manager.num_channels)
        
        # 分析所有通道
        print("DEBUG - API: Analyzing all channels")
        analysis = pid_agent.analyze_all_channels(hours)
        print(f"DEBUG - API: Analysis result: {analysis}")
        print("\n=== API: /optimization/channels/optimize END ===\n")
        return analysis
        
    except Exception as e:
        import traceback
        print(f"DEBUG - API: Optimization error: {str(e)}")
        print(f"DEBUG - API: Traceback: {traceback.format_exc()}")
        print("\n=== API: /optimization/channels/optimize END (with error) ===\n")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze channels: {str(e)}"
        )
