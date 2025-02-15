from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    SERIAL_PORT: str = Field(default="/dev/cu.usbserial-1440")
    BAUD_RATE: int = Field(default=115200)
    DEEPSEEK_API_KEY: str = Field(default="")
    API_PORT: int = Field(default=8000)
    STREAMLIT_PORT: int = Field(default=8501)
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
