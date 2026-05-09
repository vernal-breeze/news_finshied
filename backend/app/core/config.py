"""应用配置"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite:///./data/news_editor.db"

    # AI API
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "deepseek-ai/DeepSeek-V3"

    # 应用
    APP_NAME: str = "新闻内容采编系统"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-local-key"
    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # 爬虫
    CRAWLER_TIMEOUT: int = 15
    CRAWLER_RETRY_TIMES: int = 2
    CRAWLER_DELAY: float = 1.0
    CRAWLER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # 日志
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
