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
        """获取 AI API Key（优先 SiliconFlow，备用 OpenAI）"""
        return self.SILICONFLOW_API_KEY or self.OPENAI_API_KEY


@lru_cache()
def get_settings() -> Settings:
    return Settings()
