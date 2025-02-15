# llm_settings.py
import yaml
import os
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse

# 调试开关
DEBUG = True

class ModelConfig(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    max_tokens: int = Field(..., gt=0)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9-._]+$', v):
            raise ValueError('Model name must only contain letters, numbers, hyphens, dots, and underscores')
        return v

class ProviderConfig(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    api_key: Optional[str] = Field(None)
    base_url: Optional[str] = Field(None)
    models: List[ModelConfig] = Field(..., min_items=1)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9-._]+$', v):
            raise ValueError('Provider name must only contain letters, numbers, hyphens, dots, and underscores')
        return v
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^[A-Za-z0-9_-]+$', v):
                raise ValueError('API key contains invalid characters')
        return v
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            parsed = urlparse(v)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError('Invalid base URL format')
            if parsed.scheme not in ['http', 'https']:
                raise ValueError('Base URL must use HTTP or HTTPS protocol')
        return v

class LLMSettings:
    def __init__(self, config_path: str = "config/llm_config.yaml"):
        self.config_path = config_path
        self._validated_providers = {}
        self._load_config()
        self._validate_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
                if not self._config:
                    self._config = {
                        "providers": {},
                        "current": {
                            "provider": None,
                            "model": None
                        }
                    }
                if 'providers' not in self._config:
                    self._config['providers'] = {}
                if 'current' not in self._config:
                    self._config['current'] = {
                        "provider": None,
                        "model": None
                    }
        except FileNotFoundError:
            self._config = {
                "providers": {},
                "current": {
                    "provider": None,
                    "model": None
                }
            }
            self._save_config()

    def _save_config(self) -> None:
        """保存配置到文件"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # 准备配置字典
        config_dict = {
            'current': self._config.get('current', {
                'provider': None,
                'model': None
            })
        }
        
        # 如果有已验证的提供商，使用它们的配置
        if self._validated_providers:
            config_dict['providers'] = {
                name: {
                    'name': p.name,
                    'description': p.description,
                    'api_key': p.api_key,
                    'base_url': p.base_url,
                    'models': [
                        {
                            'name': m.name,
                            'description': m.description,
                            'max_tokens': m.max_tokens
                        } for m in p.models
                    ]
                } for name, p in self._validated_providers.items()
            }
        else:
            # 否则保存原始配置
            config_dict['providers'] = self._config.get('providers', {})
        
        if DEBUG:
            print(f"[DEBUG] Saving config: {json.dumps(config_dict, indent=2)}")
            
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, sort_keys=False)

    def _validate_config(self) -> None:
        """验证配置文件格式"""
        try:
            providers = {}
            for provider_name, provider_data in self._config.get('providers', {}).items():
                try:
                    # 创建模型配置
                    models = []
                    for model_data in provider_data.get('models', []):
                        try:
                            model = ModelConfig(
                                name=model_data['name'],
                                description=model_data['description'],
                                max_tokens=model_data['max_tokens']
                            )
                            models.append(model)
                        except Exception as e:
                            print(f"[WARNING] Skipping invalid model config for {model_data.get('name', 'unknown')}: {str(e)}")
                            continue
                    
                    if not models:  # 如果没有有效的模型，跳过这个提供商
                        print(f"[WARNING] Skipping provider {provider_name} as it has no valid models")
                        continue
                    
                    # 创建提供商配置
                    provider_config = {
                        'name': provider_data['name'],
                        'description': provider_data['description'],
                        'models': models
                    }
                    
                    # API key 和 base_url 可选
                    if 'api_key' in provider_data:
                        provider_config['api_key'] = provider_data['api_key']
                    if 'base_url' in provider_data:
                        provider_config['base_url'] = provider_data['base_url']
                        
                    provider = ProviderConfig(**provider_config)
                    providers[provider_name] = provider
                    print(f"[INFO] Successfully validated provider {provider_name}")
                    
                except Exception as e:
                    print(f"[WARNING] Skipping invalid provider config for {provider_name}: {str(e)}")
                    continue
                    
            if not providers:  # 如果没有有效的提供商，报错
                raise ValueError("No valid providers found in configuration")
                
            self._validated_providers = providers
            print(f"[INFO] Successfully validated {len(providers)} providers")
            
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {str(e)}")

    def get_current_config(self) -> Dict[str, Optional[str]]:
        """获取当前使用的提供商和模型"""
        return self._config['current']

    def set_current_config(self, provider_name: str, model_name: str) -> None:
        """设置当前提供商和模型"""
        if provider_name not in self._config['providers']:
            raise ValueError(f"Provider {provider_name} not found")
            
        provider_config = self._config['providers'][provider_name]
        if not any(m['name'] == model_name for m in provider_config['models']):
            raise ValueError(f"Model {model_name} not found for provider {provider_name}")
            
        self._config['current'] = {
            "provider": provider_name,
            "model": model_name
        }
        self._save_config()
        
    def get_current_provider(self) -> Optional[str]:
        """获取当前使用的提供商"""
        return self._config['current']['provider']

    def set_current_provider(self, provider_name: str) -> None:
        """设置当前提供商"""
        if provider_name not in self._config['providers']:
            raise ValueError(f"Provider {provider_name} not found")
            
        # 设置提供商，并使用其第一个模型作为默认模型
        provider_config = self._config['providers'][provider_name]
        default_model = provider_config['models'][0]['name']
        self.set_current_config(provider_name, default_model)

    def get_provider_config(self, provider_name: str) -> Dict:
        """获取指定提供商的配置"""
        if provider_name not in self._config['providers']:
            raise ValueError(f"Provider {provider_name} not found")
        return self._config['providers'][provider_name]

    def get_model_config(self, provider_name: str, model_name: str) -> Dict:
        """获取指定模型的配置"""
        provider_config = self.get_provider_config(provider_name)
        for model in provider_config['models']:
            if model['name'] == model_name:
                return model
        raise ValueError(f"Model {model_name} not found for provider {provider_name}")

    def update_provider(self, provider_name: str, api_key: str, base_url: Optional[str] = None) -> None:
        """更新提供商的配置
        
        Args:
            provider_name: 提供商名称
            api_key: API密钥
            base_url: 可选，API基础URL
        """
        if provider_name not in self._config['providers']:
            raise ValueError(f"Provider {provider_name} not found")
            
        provider = self._config['providers'][provider_name]
        if api_key:  # 只在提供 API key 时更新
            provider['api_key'] = api_key
        if base_url is not None:
            provider['base_url'] = base_url
            
        # 验证新的配置
        provider_config = ProviderConfig(**provider)
        self._validated_providers[provider_name] = provider_config
        
        self._save_config()

    def list_providers(self) -> List[str]:
        """列出所有可用的提供商"""
        # 优先使用已验证的提供商
        if self._validated_providers:
            return list(self._validated_providers.keys())
        # 否则使用原始配置
        return list(self._config['providers'].keys())

    def list_models(self, provider_name: str) -> List[str]:
        """列出指定提供商的所有可用模型"""
        provider_config = self.get_provider_config(provider_name)
        return [model['name'] for model in provider_config['models']]

    def get_api_key(self, provider_name: str) -> str:
        """获取指定提供商的API密钥"""
        provider_config = self.get_provider_config(provider_name)
        return provider_config['api_key']

    def get_base_url(self, provider_name: str) -> Optional[str]:
        """获取指定提供商的基础URL"""
        provider_config = self.get_provider_config(provider_name)
        return provider_config.get('base_url')

    def validate_provider_config(self, provider_name: str) -> bool:
        """验证提供商配置的完整性"""
        try:
            provider_config = self.get_provider_config(provider_name)
            required_fields = ['name', 'description', 'api_key', 'models']
            return all(field in provider_config for field in required_fields)
        except Exception:
            return False

# 创建全局实例
llm_settings = LLMSettings()

# 使用示例
if __name__ == "__main__":
    # 设置默认提供商和模型
    current = llm_settings.get_current_config()
    if not current["provider"]:
        print("Setting default provider and model...")
        llm_settings.set_current_config("deepseek", "deepseek-chat")
        current = llm_settings.get_current_config()
    print(f"Current config: {current}")

    # 更新API密钥
    try:
        llm_settings.update_provider("deepseek", "test-api-key")
        print("API key updated successfully")
    except ValueError as e:
        print(f"Error updating API key: {e}")

    # 获取模型配置
    try:
        model_config = llm_settings.get_model_config(current["provider"], current["model"])
        print(f"Model config: {json.dumps(model_config, indent=2)}")
    except ValueError as e:
        print(f"Error getting model config: {e}")

    # 列出所有提供商
    providers = llm_settings.list_providers()
    print(f"Available providers: {providers}")

    # 列出当前提供商的所有模型
    try:
        models = llm_settings.list_models(current["provider"])
        print(f"Available models for {current['provider']}: {models}")
    except ValueError as e:
        print(f"Error listing models: {e}")