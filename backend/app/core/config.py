"""应用配置"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite:///./data/news_editor.db"

    # ---- AI API ----
    # 主 Provider: DeepSeek 官方 API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    # 备用 Provider（聚合网关）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    # OpenAI（可选）
    OPENAI_API_KEY: str = ""
    # 通用：当前使用的模型标识
    AI_MODEL: str = "deepseek-chat"
    # 通用：API 超时（秒）
    AI_TIMEOUT: int = 60

    # 应用
    APP_NAME: str = "新闻内容采编系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-local-key"
    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # 爬虫
    CRAWLER_TIMEOUT: int = 20
    CRAWLER_RETRY_TIMES: int = 2
    CRAWLER_DELAY: float = 1.0
    CRAWLER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # 认证
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时

    # 日志
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_cors_origins(self) -> list[str]:
        """获取 CORS 来源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def get_ai_api_key(self) -> str:
        """获取主 AI API Key：优先 DeepSeek → SiliconFlow → OpenAI"""
        return self.DEEPSEEK_API_KEY or self.SILICONFLOW_API_KEY or self.OPENAI_API_KEY

    def get_ai_base_url(self, provider: str = "deepseek") -> str:
        """获取 AI API 基础 URL"""
        if provider == "deepseek":
            return self.DEEPSEEK_BASE_URL
        if provider == "siliconflow":
            return self.SILICONFLOW_BASE_URL
        return self.DEEPSEEK_BASE_URL


@lru_cache()
def get_settings() -> Settings:
    return Settings()
