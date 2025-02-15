# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 串口配置
    SERIAL_PORT: str = "/dev/cu.usbserial-1440"
    BAUD_RATE: int = 115200
    DEEPSEEK_API_KEY: str
    # 服务端口
    API_PORT: int = 8000
    STREAMLIT_PORT: int = 8501
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()