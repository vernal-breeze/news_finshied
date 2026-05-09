"""
LLM 统一调用模块 — 工厂模式 + Provider 注册表

设计目标：
  1. 新增模型只需在注册表追加一行，无需改动核心逻辑
  2. Provider 与调用逻辑彻底解耦，每个 Provider 独立维护
  3. 内置重试/降级/流式输出，所有 Provider 统一受益
  4. 向后兼容 EnhancedAIService，现有代码零改动

使用示例:
    from app.services.llm import LLMFactory

    client = LLMFactory.create("deepseek-v3")
    reply = client.chat("你好")
    async for chunk in client.stream_chat("写一篇新闻"):
        print(chunk, end="")

新增模型示例（在 PROVIDER_REGISTRY 表追加一行即可）：
    "qwen3-max": {
        "provider": "openai_compatible",
        "model_id": "Qwen/Qwen3-Max",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "max_tokens": 16384,
        "temperature_range": (0.0, 1.5),
        "tags": ["reasoning"],
    },
"""
from __future__ import annotations

import os
import re
import json
import time
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import (
    Any, AsyncIterator, Callable, Dict, Iterator, List,
    Optional, Tuple, Type, Union,
)
from dataclasses import dataclass, field
from functools import wraps

from openai import OpenAI

from app.core.config import get_settings
from app.services.rate_limiter import get_rate_limiter
from app.services.cache_service import get_ai_cache

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logger = logging.getLogger("service.llm")


# ===================================================================
# 数据模型
# ===================================================================

@dataclass
class LLMMessage:
    """统一消息格式"""
    role: str       # system / user / assistant
    content: str

    def to_openai(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMRequest:
    """统一请求"""
    messages: List[LLMMessage]
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop: Optional[List[str]] = None
    stream: bool = False
    # 缓存 & 速率控制
    cache_key: Optional[str] = None
    cache_ttl: int = 3600
    skip_cache: bool = False


@dataclass
class LLMResponse:
    """统一响应"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)  # prompt / completion / total
    finish_reason: str = "stop"
    cached: bool = False


@dataclass
class ProviderSpec:
    """Provider 注册规格

    新增模型只需实例化一个 ProviderSpec 并注册即可。
    """
    provider: str                          # provider 类型名，如 "openai_compatible"
    model_id: str                          # 实际 API model id
    base_url: str                          # API 地址
    api_key_env: str                       # API Key 环境变量名（逗号分隔可多个fallback）
    max_tokens: int = 16384
    temperature_range: Tuple[float, float] = (0.0, 2.0)
    tags: List[str] = field(default_factory=list)
    thinking_model: bool = False            # 是否为思考模型（需要更多 max_tokens）
    thinking_token_overhead: int = 500      # 思考模型额外 token 预算

    # ---- 可选覆盖 ----
    api_key: Optional[str] = None          # 直接传 key（优先级高于 env）
    extra_headers: Dict[str, str] = field(default_factory=dict)
    extra_body: Dict[str, Any] = field(default_factory=dict)


# ===================================================================
# 工具函数
# ===================================================================

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """从任意文本中提取 JSON 对象（兼容 markdown 代码块）。"""
    if not text or not text.strip():
        return None
    raw = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def retry_on_failure(max_retries: int = 3, base_delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器（指数退避）。"""
    def deco(fn: Callable):
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay
            last_exc: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        logger.warning(
                            "%s 失败 (第 %d/%d 次), %.1fs 后重试: %s",
                            fn.__name__, attempt + 1, max_retries, delay, exc,
                        )
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error("%s 最终失败 (%d 次): %s", fn.__name__, max_retries, exc)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return deco


# ===================================================================
# Provider 基类
# ===================================================================

class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, spec: ProviderSpec):
        self.spec = spec
        self._client: Optional[OpenAI] = None
        self._init_client()

    # ---- 子类必须实现 ----

    @abstractmethod
    def _resolve_api_key(self) -> Optional[str]:
        """解析 API Key。"""
        ...

    @abstractmethod
    def _build_client(self, api_key: str) -> OpenAI:
        """构建 OpenAI 兼容客户端。"""
        ...

    # ---- 公共 API ----

    def _init_client(self) -> None:
        key = self.spec.api_key or self._resolve_api_key()
        if not key:
            logger.warning("Provider %s: 未配置 API Key，降级为 Mock", self.spec.provider)
            self._client = None
            return
        try:
            self._client = self._build_client(key)
            logger.info("Provider %s 初始化成功 (model=%s)", self.spec.provider, self.spec.model_id)
        except Exception as exc:
            logger.error("Provider %s 初始化失败: %s", self.spec.provider, exc)
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def model_id(self) -> str:
        return self.spec.model_id

    @property
    def provider_name(self) -> str:
        return self.spec.provider

    def _clamp_temperature(self, t: float) -> float:
        lo, hi = self.spec.temperature_range
        return max(lo, min(hi, t))

    def _clamp_max_tokens(self, n: int) -> int:
        effective = self.spec.max_tokens
        if self.spec.thinking_model:
            effective = max(effective, n + self.spec.thinking_token_overhead)
        return max(1, min(n, effective))

    def chat(self, req: LLMRequest) -> LLMResponse:
        """同步对话。"""
        if not self._client:
            return self._mock_chat(req)
        return self._do_chat(req)

    def stream_chat(self, req: LLMRequest) -> Iterator[str]:
        """同步流式对话（返回迭代器）。"""
        if not self._client:
            yield from self._mock_stream(req)
            return
        yield from self._do_stream(req)

    # ---- 内部 ----

    def _to_openai_messages(self, req: LLMRequest) -> List[Dict[str, str]]:
        return [m.to_openai() for m in req.messages]

    @retry_on_failure(max_retries=3, base_delay=2.0, backoff=2.0)
    def _do_chat(self, req: LLMRequest) -> LLMResponse:
        assert self._client is not None
        # 思考模型需要更多 token 预算
        effective_max_tokens = req.max_tokens
        if self.spec.thinking_model:
            effective_max_tokens = max(req.max_tokens, req.max_tokens + self.spec.thinking_token_overhead)
        resp = self._client.chat.completions.create(
            model=self.model_id,
            messages=self._to_openai_messages(req),
            temperature=self._clamp_temperature(req.temperature),
            max_tokens=self._clamp_max_tokens(effective_max_tokens),
            top_p=req.top_p,
            stop=req.stop,
            extra_headers=self.spec.extra_headers or None,
            extra_body=self.spec.extra_body or None,
        )
        choice = resp.choices[0]
        usage = resp.usage
        content = choice.message.content or ""
        # 兼容思考模型：content 为空时尝试从 reasoning 提取最后一段
        if not content and hasattr(choice.message, 'reasoning'):
            reasoning = getattr(choice.message, 'reasoning', '') or ''
            if reasoning:
                # 提取 reasoning 中最后一个实质性段落（通常是模型最终结论）
                lines = reasoning.strip().split('\n')
                # 从末尾找非空行
                for line in reversed(lines):
                    stripped = line.strip()
                    if stripped and len(stripped) > 2 and not stripped.startswith('*') and 'Draft' not in stripped:
                        content = stripped
                        break
                # 兜底：取 reasoning 最后 200 字符
                if not content:
                    content = reasoning.strip()[-200:]
        return LLMResponse(
            content=content,
            model=resp.model,
            usage={
                "prompt": usage.prompt_tokens if usage else 0,
                "completion": usage.completion_tokens if usage else 0,
                "total": usage.total_tokens if usage else 0,
            },
            finish_reason=choice.finish_reason or "stop",
        )

    def _do_stream(self, req: LLMRequest) -> Iterator[str]:
        assert self._client is not None
        stream = self._client.chat.completions.create(
            model=self.model_id,
            messages=self._to_openai_messages(req),
            temperature=self._clamp_temperature(req.temperature),
            max_tokens=self._clamp_max_tokens(req.max_tokens),
            top_p=req.top_p,
            stop=req.stop,
            stream=True,
            extra_headers=self.spec.extra_headers or None,
            extra_body=self.spec.extra_body or None,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    # ---- Mock 降级 ----

    def _mock_chat(self, req: LLMRequest) -> LLMResponse:
        user_text = req.messages[-1].content if req.messages else ""
        return LLMResponse(
            content=f"【Mock 响应】Provider '{self.provider_name}' 未配置。您的输入：{user_text[:200]}",
            model="mock",
            cached=False,
        )

    def _mock_stream(self, req: LLMRequest) -> Iterator[str]:
        user_text = req.messages[-1].content if req.messages else ""
        for word in user_text[:300]:
            yield word
            time.sleep(0.01)
        yield "\n\n【流式 Mock 完成】"


# ===================================================================
# 内置 Provider 实现
# ===================================================================

class SiliconFlowProvider(BaseLLMProvider):
    """SiliconFlow（OpenAI 兼容协议）。"""

    def _resolve_api_key(self) -> Optional[str]:
        settings = get_settings()
        return settings.SILICONFLOW_API_KEY or settings.OPENAI_API_KEY

    def _build_client(self, api_key: str) -> OpenAI:
        settings = get_settings()
        return OpenAI(
            api_key=api_key,
            base_url=getattr(settings, "SILICONFLOW_BASE_URL",
                             "https://api.siliconflow.cn/v1"),
            timeout=getattr(settings, "AI_TIMEOUT", 30),
        )


class OpenAIProvider(BaseLLMProvider):
    """原生 OpenAI。"""

    def _resolve_api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")

    def _build_client(self, api_key: str) -> OpenAI:
        return OpenAI(
            api_key=api_key,
            timeout=getattr(get_settings(), "AI_TIMEOUT", 30),
        )


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter 聚合网关（OpenAI 兼容协议）。"""

    def _resolve_api_key(self) -> Optional[str]:
        return os.getenv("OPENROUTER_API_KEY")

    def _build_client(self, api_key: str) -> OpenAI:
        return OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=getattr(get_settings(), "AI_TIMEOUT", 30),
            default_headers={
                "HTTP-Referer": "https://news-editor.local",
                "X-Title": "News Editor System",
            },
        )


class MoonshotProvider(BaseLLMProvider):
    """Kimi / Moonshot（OpenAI 兼容协议）。"""

    def _resolve_api_key(self) -> Optional[str]:
        return os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENAI_API_KEY")

    def _build_client(self, api_key: str) -> OpenAI:
        return OpenAI(
            api_key=api_key,
            base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
            timeout=getattr(get_settings(), "AI_TIMEOUT", 30),
        )


class OllamaProvider(BaseLLMProvider):
    """本地 Ollama（优先使用原生 API，避免 OpenAI 兼容层的 thinking 模型问题）。"""

    def _resolve_api_key(self) -> Optional[str]:
        return "ollama"  # Ollama 不需要真实 Key，但需要非空值通过 Mock 检查

    def _build_client(self, api_key: str) -> OpenAI:
        return OpenAI(
            api_key=api_key,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            timeout=getattr(get_settings(), "AI_TIMEOUT", 120),
        )

    @retry_on_failure(max_retries=3, base_delay=2.0, backoff=2.0)
    def _do_chat(self, req: LLMRequest) -> LLMResponse:
        """使用 Ollama 原生 /api/chat 端点，避免 OpenAI 兼容层的 502 问题"""
        import requests as http_requests
        
        ollama_messages = []
        for m in req.messages:
            msg = {"role": m.role, "content": m.content}
            ollama_messages.append(msg)
        
        payload = {
            "model": self.model_id,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": min(req.max_tokens, self.spec.max_tokens),
            },
        }
        if req.temperature is not None:
            payload["options"]["temperature"] = req.temperature
        if req.top_p is not None:
            payload["options"]["top_p"] = req.top_p
        
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/v1")
        resp = http_requests.post(
            f"{base}/api/chat",
            json=payload,
            timeout=getattr(get_settings(), "AI_TIMEOUT", 120),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama API error: {resp.status_code} - {resp.text[:200]}")
        
        data = resp.json()
        content = data.get("message", {}).get("content", "") or ""
        eval_count = data.get("eval_count", 0)
        
        return LLMResponse(
            content=content,
            model=data.get("model", self.model_id),
            usage={
                "prompt": data.get("prompt_eval_count", 0),
                "completion": eval_count,
                "total": data.get("prompt_eval_count", 0) + eval_count,
            },
            finish_reason=data.get("done_reason", "stop"),
        )


# ===================================================================
# Provider 注册表
# ===================================================================

class ProviderRegistry:
    """Provider 注册表 — 全局单例。

    新增模型只需调用 register()：

        from app.services.llm import provider_registry, ProviderSpec, SiliconFlowProvider
        provider_registry.register("qwen3", ProviderSpec(
            provider="siliconflow", model_id="Qwen/Qwen3-Max", ...
        ), SiliconFlowProvider)
    """

    _instance: Optional["ProviderRegistry"] = None

    def __init__(self):
        self._providers: Dict[str, Type[BaseLLMProvider]] = {}
        self._specs: Dict[str, ProviderSpec] = {}
        self._instances: Dict[str, BaseLLMProvider] = {}

    # ---- 单例 ----

    @classmethod
    def get(cls) -> "ProviderRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ---- 注册 ----

    def register(
        self,
        key: str,
        spec: ProviderSpec,
        provider_cls: Type[BaseLLMProvider],
        *,
        override: bool = False,
    ) -> None:
        """注册一个模型。

        Args:
            key: 模型别名（如 "deepseek-v3"）
            spec: Provider 规格
            provider_cls: Provider 实现类
            override: 是否覆盖已有注册
        """
        if key in self._specs and not override:
            raise ValueError(f"模型 '{key}' 已注册，使用 override=True 覆盖")
        self._specs[key] = spec
        self._providers[key] = provider_cls
        self._instances.pop(key, None)  # 清除旧实例
        logger.info("Provider 注册: %s → %s/%s", key, spec.provider, spec.model_id)

    def unregister(self, key: str) -> None:
        self._specs.pop(key, None)
        self._providers.pop(key, None)
        self._instances.pop(key, None)

    def get_spec(self, key: str) -> ProviderSpec:
        if key not in self._specs:
            raise KeyError(f"未注册的模型: {key}，可用: {list(self._specs.keys())}")
        return self._specs[key]

    def get_instance(self, key: str) -> BaseLLMProvider:
        """获取或创建 Provider 实例（懒加载 + 缓存）。"""
        if key not in self._instances:
            spec = self.get_spec(key)
            cls = self._providers[key]
            self._instances[key] = cls(spec)
        return self._instances[key]

    def keys(self) -> List[str]:
        return list(self._specs.keys())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": k,
                "provider": s.provider,
                "model_id": s.model_id,
                "max_tokens": s.max_tokens,
                "tags": s.tags,
                "available": self.get_instance(k).available,
            }
            for k, s in self._specs.items()
        ]

    def clear(self) -> None:
        """仅测试用。"""
        self._specs.clear()
        self._providers.clear()
        self._instances.clear()


# ---- 全局单例 ----
provider_registry = ProviderRegistry.get()


# ===================================================================
# 默认注册（项目内置模型）
# ===================================================================

def _register_defaults() -> None:
    settings = get_settings()
    sf_base = getattr(settings, "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

    defaults: Dict[str, Tuple[ProviderSpec, Type[BaseLLMProvider]]] = {
        # ---- DeepSeek 系列（via SiliconFlow）----
        "deepseek-v3": (
            ProviderSpec(
                provider="siliconflow",
                model_id="deepseek-ai/DeepSeek-V3",
                base_url=sf_base,
                api_key_env="SILICONFLOW_API_KEY,OPENAI_API_KEY",
                max_tokens=8192,
                temperature_range=(0.0, 1.5),
                tags=["general", "fast"],
            ),
            SiliconFlowProvider,
        ),
        "deepseek-r1": (
            ProviderSpec(
                provider="siliconflow",
                model_id="deepseek-ai/DeepSeek-R1",
                base_url=sf_base,
                api_key_env="SILICONFLOW_API_KEY,OPENAI_API_KEY",
                max_tokens=8192,
                temperature_range=(0.0, 1.5),
                tags=["reasoning"],
            ),
            SiliconFlowProvider,
        ),
        # ---- Qwen 系列（via SiliconFlow）----
        "qwen-plus": (
            ProviderSpec(
                provider="siliconflow",
                model_id="Qwen/Qwen2.5-72B-Instruct",
                base_url=sf_base,
                api_key_env="SILICONFLOW_API_KEY,OPENAI_API_KEY",
                max_tokens=16384,
                temperature_range=(0.0, 1.5),
                tags=["general", "chinese"],
            ),
            SiliconFlowProvider,
        ),
        "qwen-max": (
            ProviderSpec(
                provider="siliconflow",
                model_id="Qwen/Qwen2.5-72B-Instruct",
                base_url=sf_base,
                api_key_env="SILICONFLOW_API_KEY,OPENAI_API_KEY",
                max_tokens=16384,
                temperature_range=(0.0, 1.5),
                tags=["general", "chinese"],
            ),
            SiliconFlowProvider,
        ),
        # ---- OpenAI 系列 ----
        "gpt-4o": (
            ProviderSpec(
                provider="openai",
                model_id="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key_env="OPENAI_API_KEY",
                max_tokens=16384,
                temperature_range=(0.0, 2.0),
                tags=["general", "multimodal"],
            ),
            OpenAIProvider,
        ),
        "gpt-4o-mini": (
            ProviderSpec(
                provider="openai",
                model_id="gpt-4o-mini",
                base_url="https://api.openai.com/v1",
                api_key_env="OPENAI_API_KEY",
                max_tokens=16384,
                temperature_range=(0.0, 2.0),
                tags=["general", "fast", "cheap"],
            ),
            OpenAIProvider,
        ),
        # ---- Kimi / Moonshot ----
        "kimi": (
            ProviderSpec(
                provider="moonshot",
                model_id="moonshot-v1-8k",
                base_url="https://api.moonshot.cn/v1",
                api_key_env="KIMI_API_KEY,MOONSHOT_API_KEY",
                max_tokens=8192,
                temperature_range=(0.0, 1.0),
                tags=["chinese", "kimi"],
            ),
            MoonshotProvider,
        ),
        # ---- 本地 Ollama ----
        "ollama-qwen": (
            ProviderSpec(
                provider="ollama",
                model_id="qwen3.5:4b",
                base_url="http://localhost:11434/v1",
                api_key_env="",
                max_tokens=8192,
                temperature_range=(0.0, 1.5),
                tags=["local", "free", "chinese"],
                thinking_model=True,
                thinking_token_overhead=6000,
            ),
            OllamaProvider,
        ),
    }

    for key, (spec, cls) in defaults.items():
        try:
            provider_registry.register(key, spec, cls)
        except ValueError:
            pass  # 已注册则跳过（如测试环境重复加载）


_register_defaults()


# ===================================================================
# 降级映射
# ===================================================================

FALLBACK_MAP: Dict[str, str] = {
    "deepseek-r1": "deepseek-v3",
    "qwen-plus": "qwen-max",
    "gpt-4o": "gpt-4o-mini",
    "kimi": "ollama-qwen",
}


# ===================================================================
# LLM 工厂
# ===================================================================

class LLMFactory:
    """LLM 工厂 — 创建配置好的 LLM 客户端。

    用法:
        client = LLMFactory.create("deepseek-v3")
        # 或使用默认模型
        client = LLMFactory.create()
    """

    DEFAULT_KEY = "deepseek-v3"

    # ---- 创建 ----

    @classmethod
    def create(cls, model_key: Optional[str] = None) -> "LLMClient":
        """创建 LLM 客户端。

        Args:
            model_key: 模型别名，默认使用配置中的 AI_MODEL。
        """
        if model_key is None:
            settings = get_settings()
            model_key = cls._resolve_config_key(getattr(settings, "AI_MODEL", cls.DEFAULT_KEY))
        return LLMClient(model_key=model_key)

    # ---- 辅助 ----

    @classmethod
    def _resolve_config_key(cls, raw: str) -> str:
        """将 config 中的 model_id 反向解析为注册 key。"""
        # 直接匹配 key
        if raw in provider_registry._specs:
            return raw
        # 别名映射
        aliases = {
            "deepseek-ai/DeepSeek-V3": "deepseek-v3",
            "deepseek-ai/DeepSeek-R1": "deepseek-r1",
            "Qwen/Qwen2.5-72B-Instruct": "qwen-plus",
            "Qwen/Qwen2.5-7B-Instruct": "qwen-plus",
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
        }
        return aliases.get(raw, cls.DEFAULT_KEY)

    @classmethod
    def list_models(cls) -> List[Dict[str, Any]]:
        return provider_registry.list_models()


# ===================================================================
# LLM 客户端（统一入口）
# ===================================================================

class LLMClient:
    """LLM 统一客户端 — 封装 Provider、缓存、速率限制、降级。

    这是业务代码唯一需要使用的入口。
    """

    def __init__(self, model_key: str):
        self.model_key = model_key
        self.fallback_key: Optional[str] = FALLBACK_MAP.get(model_key)
        self._provider: Optional[BaseLLMProvider] = None
        self._cache = get_ai_cache()
        self._rate_limiter = get_rate_limiter()

    # ---- provider 懒加载 ----

    @property
    def provider(self) -> BaseLLMProvider:
        if self._provider is None:
            self._provider = provider_registry.get_instance(self.model_key)
        return self._provider

    @property
    def available(self) -> bool:
        return self.provider.available

    # ---- 缓存 ----

    def _cache_get(self, operation: str, **params: Any) -> Optional[str]:
        return self._cache.get(operation, **params)

    def _cache_set(self, operation: str, value: str, ttl: int = 3600, **params: Any) -> None:
        self._cache.set(operation, value, ttl=ttl, **params)

    # ---- 核心 API ----

    def chat(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        cache: bool = False,
        cache_ttl: int = 3600,
    ) -> str:
        """同步对话（便捷方法）。

        Args:
            prompt: 用户输入
            system: 系统提示
            temperature: 温度（None=默认）
            max_tokens: 最大 token（None=默认）
            cache: 是否缓存
            cache_ttl: 缓存 TTL（秒）
        """
        # 查缓存
        if cache:
            cached = self._cache_get("chat", prompt=prompt, system=system)
            if cached:
                return cached

        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))

        req = LLMRequest(
            messages=messages,
            temperature=temperature if temperature is not None else 0.7,
            max_tokens=max_tokens or 4096,
        )

        # 主模型
        try:
            resp = self.provider.chat(req)
            result = resp.content
            if cache and result:
                self._cache_set("chat", result, ttl=cache_ttl, prompt=prompt, system=system)
            return result
        except Exception as exc:
            logger.warning("模型 %s 调用失败: %s", self.model_key, exc)
            # 尝试降级
            if self.fallback_key and self.fallback_key != self.model_key:
                logger.info("降级到 %s", self.fallback_key)
                try:
                    fallback = provider_registry.get_instance(self.fallback_key)
                    resp = fallback.chat(req)
                    return resp.content
                except Exception as exc2:
                    logger.error("降级模型 %s 也失败: %s", self.fallback_key, exc2)
            return f"【生成失败】模型调用异常: {exc}"

    def chat_with_json(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.4,
        max_tokens: Optional[int] = None,
        cache: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """对话并解析为 JSON。

        Returns:
            解析成功返回 dict，失败返回 None。
        """
        result = self.chat(
            prompt=prompt,
            system=system + "\n请只输出合法 JSON，不要使用 Markdown 代码块。",
            temperature=temperature,
            max_tokens=max_tokens,
            cache=cache,
        )
        return _extract_json(result)

    def stream_chat(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """同步流式对话（返回迭代器，用于 SSE）。"""
        messages = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))

        # 思考模型自动增加 token 预算
        effective_max = max_tokens or 4096
        if self.provider.spec.thinking_model:
            effective_max = max(effective_max, 2048)

        req = LLMRequest(
            messages=messages,
            temperature=temperature if temperature is not None else 0.7,
            max_tokens=effective_max,
            stream=True,
        )
        try:
            yield from self.provider.stream_chat(req)
        except Exception as exc:
            logger.warning("模型 %s 流式调用失败: %s", self.model_key, exc)
            yield f"\n\n【流式中断】{exc}"

    # ---- 批量 ----

    def batch_chat(
        self,
        prompts: List[str],
        *,
        system: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> List[str]:
        """批量对话（顺序执行）。"""
        return [
            self.chat(p, system=system, temperature=temperature, max_tokens=max_tokens)
            for p in prompts
        ]


# ===================================================================
# 向后兼容层 — EnhancedAIService 适配器
# ===================================================================

class LLMBackendAdapter:
    """向后兼容适配器 — 让现有 EnhancedAIService 代码零改动接入新架构。

    使用方式（在 services/__init__.py 中替换导入即可）:
        from app.services.llm import LLMBackendAdapter
        ai_service = LLMBackendAdapter()
    """

    def __init__(self, model_key: Optional[str] = None):
        self._client = LLMFactory.create(model_key)
        self._model_key = model_key or LLMFactory._resolve_config_key(
            getattr(get_settings(), "AI_MODEL", "deepseek-v3")
        )

    @property
    def client(self) -> LLMClient:
        return self._client

    def chat(self, prompt: str, *, system: str = "", **kwargs: Any) -> str:
        return self._client.chat(prompt, system=system, **kwargs)

    def chat_json(self, prompt: str, *, system: str = "", **kwargs: Any) -> Optional[Dict[str, Any]]:
        return self._client.chat_with_json(prompt, system=system, **kwargs)

    def stream(self, prompt: str, *, system: str = "", **kwargs: Any) -> Iterator[str]:
        return self._client.stream_chat(prompt, system=system, **kwargs)
