import pytest
from fastapi.testclient import TestClient
from fastapi_app.main import app
import json
import time
from fastapi_app.utils.serial_comm import SerialManager

client = TestClient(app)

def test_device_connection():
    """测试设备连接"""
    response = client.post("/api/device/connect")
    assert response.status_code == 200
    assert response.json()["status"] == "connected"

def test_device_status():
    """测试获取设备状态"""
    response = client.get("/api/device/status")
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data
    assert "pid_params" in data
    assert "timestamp" in data

def test_pid_parameter_update():
    """测试PID参数更新"""
    params = {
        "kp": 2.0,
        "ki": 0.15,
        "kd": 0.05,
        "target_temp": 50.0
    }
    response = client.post("/api/device/pid/update", json=params)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_temperature_control():
    """测试温度控制过程"""
    # 连接设备
    client.post("/api/device/connect")
    
    # 设置目标温度
    params = {
        "kp": 2.0,
        "ki": 0.15,
        "kd": 0.05,
        "target_temp": 50.0
    }
    client.post("/api/device/pid/update", json=params)
    
    # 监控温度变化
    initial_temp = None
    for _ in range(10):
        response = client.get("/api/device/status")
        data = response.json()
        current_temp = data["temperature"]
        
        if initial_temp is None:
            initial_temp = current_temp
        
        # 检查温度是否在向目标温度变化
        if _ > 5:  # 给系统一些响应时间
            assert abs(current_temp - params["target_temp"]) < abs(initial_temp - params["target_temp"])
        
        time.sleep(0.5)

def test_optimization_suggestion():
    """测试优化建议功能"""
    # 先运行系统一段时间
    client.post("/api/device/connect")
    time.sleep(2)
    
    # 获取当前状态
    response = client.get("/api/device/status")
    system_state = response.json()
    
    # 获取优化建议
    response = client.post("/api/device/optimize", json=system_state)
    assert response.status_code == 200
    suggestion = response.json()
    
    assert "metrics" in suggestion
    assert "optimization" in suggestion

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
