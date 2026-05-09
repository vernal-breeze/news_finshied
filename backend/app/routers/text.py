"""
文本翻译 & 处理模块 — Blueprint Router

提供统一的文本处理 API（翻译、摘要、润色、提取）。
全部端点支持 SSE 流式输出，实时反馈处理进度。

端点:
  POST /api/text/translate      翻译文本
  POST /api/text/summarize      摘要/概括
  POST /api/text/polish         润色/改进
  POST /api/text/extract        提取关键词/实体
  POST /api/text/expand         扩写
  GET  /api/text/languages      支持的语言列表
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Iterator, List, Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.services.llm import LLMFactory, LLMClient, _extract_json
from app.core.exceptions import (
    BaseAPIException,
    BadRequestException, raise_bad_request, AIServiceError,
)
from app.core.config import get_settings

# ---------------------------------------------------------------------------
logger = logging.getLogger("router.text")
router = APIRouter(prefix="/api/text", tags=["文本处理"])


# ===================================================================
# 请求 / 响应模型
# ===================================================================

class TranslateRequest(BaseModel):
    """翻译请求"""
    text: str = Field(..., min_length=1, max_length=30000, description="待翻译文本")
    source_lang: str = Field(default="auto", description="源语言（auto 自动检测）")
    target_lang: str = Field(default="en", description="目标语言")
    style: str = Field(default="neutral", description="翻译风格: neutral/formal/casual/literal")
    stream: bool = Field(default=True, description="是否 SSE 流式返回")
    model: str = Field(default="", description="指定模型 key，留空使用默认")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("文本不能为空")
        return v.strip()


class SummarizeRequest(BaseModel):
    """摘要请求"""
    text: str = Field(..., min_length=1, max_length=50000, description="待摘要文本")
    max_length: int = Field(default=200, ge=50, le=2000, description="摘要最大字数")
    style: str = Field(default="abstract", description="摘要风格: abstract/bullet/tldr/headline")
    stream: bool = Field(default=True, description="是否 SSE 流式返回")
    model: str = Field(default="", description="指定模型 key，留空使用默认")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("文本不能为空")
        return v.strip()


class PolishRequest(BaseModel):
    """润色请求"""
    text: str = Field(..., min_length=1, max_length=30000, description="待润色文本")
    mode: str = Field(default="general", description="润色模式: general/formal/academic/news/social")
    focus: Optional[str] = Field(default=None, description="重点关注: clarity/conciseness/engagement/accuracy")
    stream: bool = Field(default=True, description="是否 SSE 流式返回")
    model: str = Field(default="", description="指定模型 key，留空使用默认")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("文本不能为空")
        return v.strip()


class ExpandRequest(BaseModel):
    """扩写请求"""
    text: str = Field(..., min_length=1, max_length=10000, description="待扩写文本")
    target_length: int = Field(default=500, ge=100, le=5000, description="目标字数")
    direction: str = Field(default="general", description="扩写方向: general/detail/examples/background/analysis")
    stream: bool = Field(default=True, description="是否 SSE 流式返回")
    model: str = Field(default="", description="指定模型 key，留空使用默认")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("文本不能为空")
        return v.strip()


class ExtractRequest(BaseModel):
    """提取请求"""
    text: str = Field(..., min_length=1, max_length=30000, description="待提取文本")
    extract_type: str = Field(default="keywords", description="提取类型: keywords/entities/summary/quotes")
    count: int = Field(default=10, ge=1, le=50, description="提取数量上限")
    model: str = Field(default="", description="指定模型 key，留空使用默认")


class TextResponse(BaseModel):
    """统一响应"""
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: float = 0.0
    model: str = ""


# ===================================================================
# 语言配置
# ===================================================================

# 支持的语言
LANGUAGE_MAP: Dict[str, str] = {
    "auto": "自动检测",
    "zh": "中文",
    "zh-CN": "中文（简体）",
    "zh-TW": "中文（繁体）",
    "en": "英文",
    "ja": "日文",
    "ko": "韩文",
    "fr": "法文",
    "de": "德文",
    "es": "西班牙文",
    "ru": "俄文",
    "ar": "阿拉伯文",
    "pt": "葡萄牙文",
    "it": "意大利文",
    "th": "泰文",
    "vi": "越南文",
    "id": "印尼文",
    "ms": "马来文",
}

# 翻译风格提示
STYLE_PROMPTS: Dict[str, str] = {
    "neutral": "保持原文语气，自然流畅",
    "formal": "使用正式、书面化的表达",
    "casual": "使用口语化、轻松的表达",
    "literal": "尽量直译，忠实原文结构",
}

# 摘要风格提示
SUMMARY_STYLE_PROMPTS: Dict[str, str] = {
    "abstract": "用一段话概括核心内容",
    "bullet": "用要点列表（bullet points）概括",
    "tldr": "极度精简，一句话总结",
    "headline": "用新闻标题风格概括，2-3 条",
}

# 润色模式提示
POLISH_MODE_PROMPTS: Dict[str, str] = {
    "general": "全面优化：改善用词、句式、逻辑和可读性",
    "formal": "转为正式书面语风格",
    "academic": "转为学术论文风格",
    "news": "转为新闻稿件风格：客观、简洁、倒金字塔",
    "social": "转为社交媒体风格：生动、有网感",
}

# 扩写方向提示
EXPAND_DIRECTION_PROMPTS: Dict[str, str] = {
    "general": "全面扩展：增加细节、背景、分析和案例",
    "detail": "增加具体细节和描述",
    "examples": "增加案例和实例说明",
    "background": "增加背景信息和上下文",
    "analysis": "增加深度分析和解读",
}


# ===================================================================
# 工具函数
# ===================================================================

def _get_client(model: str = "") -> LLMClient:
    """获取 LLM 客户端（统一入口）。
    
    Args:
        model: 指定模型 key，留空则使用配置默认值
    """
    from app.services.llm import provider_registry
    settings = get_settings()
    if model and model in provider_registry._specs:
        model_key = model
    else:
        model_key = LLMFactory._resolve_config_key(getattr(settings, "AI_MODEL", "deepseek-v3"))
    return LLMFactory.create(model_key)


def _sse_event(event: str, data: Any) -> str:
    """构造一条 SSE 事件。

    Args:
        event: 事件类型 (progress / chunk / done / error)
        data: 事件数据（dict 或 str）
    """
    if isinstance(data, dict):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = json.dumps({"content": str(data)}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _sse_stream(
    generator: Iterator[str],
    *,
    progress_events: Optional[List[Dict[str, Any]]] = None,
) -> Iterator[str]:
    """将文本迭代器封装为标准 SSE 流。

    Args:
        generator: 文本块迭代器
        progress_events: 可选的进度事件列表（在流开始前发送）
    """
    # 发送进度事件
    if progress_events:
        for evt in progress_events:
            yield _sse_event("progress", evt)

    # 发送文本块
    for chunk in generator:
        if chunk:
            yield _sse_event("chunk", chunk)

    # 发送结束事件
    yield _sse_event("done", {"status": "completed"})


def _sse_error(message: str, code: str = "error") -> Iterator[str]:
    """生成 SSE 错误流。"""
    yield _sse_event("error", {"message": message, "code": code})
    yield _sse_event("done", {"status": "error"})


def _non_stream_response(data: Dict[str, Any], elapsed: float, model: str) -> TextResponse:
    """构造非流式响应。"""
    return TextResponse(data=data, elapsed_ms=round(elapsed * 1000, 1), model=model)


# ===================================================================
# API 端点
# ===================================================================

@router.get("/languages")
async def list_languages():
    """列出支持的语言。"""
    return {
        "success": True,
        "data": {
            "languages": [
                {"code": k, "name": v} for k, v in LANGUAGE_MAP.items()
            ],
            "styles": {
                "translate": list(STYLE_PROMPTS.keys()),
                "summarize": list(SUMMARY_STYLE_PROMPTS.keys()),
                "polish": list(POLISH_MODE_PROMPTS.keys()),
                "expand": list(EXPAND_DIRECTION_PROMPTS.keys()),
            },
        },
    }


# ---- 翻译 ----

@router.post("/translate")
async def translate_text(req: TranslateRequest):
    """翻译文本（支持 SSE 流式输出）。

    源语言自动检测时，会先识别语言再翻译。
    """
    t0 = time.time()
    client = _get_client(req.model)
    src_name = LANGUAGE_MAP.get(req.source_lang, req.source_lang)
    tgt_name = LANGUAGE_MAP.get(req.target_lang, req.target_lang)
    style_hint = STYLE_PROMPTS.get(req.style, STYLE_PROMPTS["neutral"])

    system = (
        f"你是一名专业翻译。请将以下文本从{src_name}翻译成{tgt_name}。"
        f"翻译风格：{style_hint}。"
        f"只输出译文，不要添加解释、标注或原文。"
    )
    prompt = req.text

    if not req.stream:
        result = client.chat(prompt, system=system, temperature=0.2, max_tokens=8192)
        return _non_stream_response(
            {"translated": result},
            time.time() - t0,
            client.model_key,
        )

    # SSE 流式
    progress = [
        {"stage": "translate", "message": f"正在翻译 ({src_name} → {tgt_name})…", "percent": 0},
        {"stage": "translate", "message": "翻译中…", "percent": 50},
    ]
    try:
        generator = client.stream_chat(prompt, system=system, temperature=0.2, max_tokens=8192)
        return StreamingResponse(
            _sse_stream(generator, progress_events=progress),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    except Exception as exc:
        logger.exception("翻译失败")
        return StreamingResponse(
            _sse_error(str(exc), "translate_error"),
            media_type="text/event-stream",
        )


# ---- 摘要 ----

@router.post("/summarize")
async def summarize_text(req: SummarizeRequest):
    """文本摘要 / 概括（支持 SSE 流式输出）。"""
    t0 = time.time()
    client = _get_client(req.model)
    style_desc = SUMMARY_STYLE_PROMPTS.get(req.style, SUMMARY_STYLE_PROMPTS["abstract"])

    system = (
        f"你是一名专业文字编辑，擅长提炼核心信息。"
        f"请为以下文本生成摘要：{style_desc}。"
        f"摘要控制在 {req.max_length} 字以内。"
        f"只输出摘要本身，不要加标题或说明。"
    )
    prompt = req.text

    if not req.stream:
        result = client.chat(prompt, system=system, temperature=0.3, max_tokens=min(req.max_length * 2, 4096))
        return _non_stream_response(
            {"summary": result, "max_length": req.max_length, "style": req.style},
            time.time() - t0,
            client.model_key,
        )

    progress = [
        {"stage": "summarize", "message": "正在分析文本结构…", "percent": 0},
        {"stage": "summarize", "message": "提取核心要点…", "percent": 30},
        {"stage": "summarize", "message": "生成摘要…", "percent": 70},
    ]
    try:
        generator = client.stream_chat(
            prompt, system=system, temperature=0.3,
            max_tokens=min(req.max_length * 2, 4096),
        )
        return StreamingResponse(
            _sse_stream(generator, progress_events=progress),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )
    except Exception as exc:
        logger.exception("摘要失败")
        return StreamingResponse(_sse_error(str(exc), "summarize_error"), media_type="text/event-stream")


# ---- 润色 ----

@router.post("/polish")
async def polish_text(req: PolishRequest):
    """润色 / 改进文本（支持 SSE 流式输出）。"""
    t0 = time.time()
    client = _get_client(req.model)
    mode_desc = POLISH_MODE_PROMPTS.get(req.mode, POLISH_MODE_PROMPTS["general"])
    focus_hint = ""
    if req.focus:
        focus_map = {
            "clarity": "重点提升语言清晰度",
            "conciseness": "重点精简冗余表达",
            "engagement": "重点增强可读性和吸引力",
            "accuracy": "重点修正错误和不准确之处",
        }
        focus_hint = f" 特别注意：{focus_map.get(req.focus, req.focus)}。"

    system = (
        f"你是一名专业文字编辑。请对以下文本进行润色优化。"
        f"优化方向：{mode_desc}。{focus_hint}"
        f"只输出润色后的文本，不要加解释或标注。"
    )
    prompt = req.text

    if not req.stream:
        result = client.chat(prompt, system=system, temperature=0.4, max_tokens=8192)
        return _non_stream_response(
            {"polished": result, "mode": req.mode},
            time.time() - t0,
            client.model_key,
        )

    progress = [
        {"stage": "polish", "message": "分析文本风格…", "percent": 0},
        {"stage": "polish", "message": "优化表达…", "percent": 40},
    ]
    try:
        generator = client.stream_chat(prompt, system=system, temperature=0.4, max_tokens=8192)
        return StreamingResponse(
            _sse_stream(generator, progress_events=progress),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )
    except Exception as exc:
        logger.exception("润色失败")
        return StreamingResponse(_sse_error(str(exc), "polish_error"), media_type="text/event-stream")


# ---- 扩写 ----

@router.post("/expand")
async def expand_text(req: ExpandRequest):
    """文本扩写（支持 SSE 流式输出）。"""
    t0 = time.time()
    client = _get_client(req.model)
    direction_desc = EXPAND_DIRECTION_PROMPTS.get(req.direction, EXPAND_DIRECTION_PROMPTS["general"])

    system = (
        f"你是一名专业内容创作者。请对以下文本进行扩写。"
        f"扩写方向：{direction_desc}。"
        f"目标字数：约 {req.target_length} 字。"
        f"保持原文核心信息不变，只输出扩写后的完整文本。"
    )
    prompt = req.text

    if not req.stream:
        result = client.chat(prompt, system=system, temperature=0.5, max_tokens=min(req.target_length * 2, 8192))
        return _non_stream_response(
            {"expanded": result, "target_length": req.target_length, "direction": req.direction},
            time.time() - t0,
            client.model_key,
        )

    progress = [
        {"stage": "expand", "message": "分析原文结构…", "percent": 0},
        {"stage": "expand", "message": f"按「{direction_desc}」方向扩写…", "percent": 30},
    ]
    try:
        generator = client.stream_chat(
            prompt, system=system, temperature=0.5,
            max_tokens=min(req.target_length * 2, 8192),
        )
        return StreamingResponse(
            _sse_stream(generator, progress_events=progress),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )
    except Exception as exc:
        logger.exception("扩写失败")
        return StreamingResponse(_sse_error(str(exc), "expand_error"), media_type="text/event-stream")


# ---- 提取 ----

@router.post("/extract")
async def extract_from_text(req: ExtractRequest):
    """从文本中提取关键词 / 实体 / 引用等信息。"""
    t0 = time.time()
    client = _get_client(req.model)

    type_config = {
        "keywords": {
            "label": "关键词",
            "format": "关键词数组",
            "system": f"你是一名信息分析师。从以下文本中提取最多 {req.count} 个关键词，直接返回 JSON 数组，不要其他内容。示例：[\"关键词1\", \"关键词2\"]",
        },
        "entities": {
            "label": "实体",
            "format": "实体对象数组",
            "system": f"你是一名 NLP 专家。从以下文本中提取命名实体（人名、地名、组织、时间、数字等），以 JSON 数组返回对象。格式：[{{\"name\": \"...\", \"type\": \"person/location/organization/date/money\"}}]",
        },
        "summary": {
            "label": "要点摘要",
            "format": "要点数组",
            "system": f"从以下文本中提取 {req.count} 个关键要点，以 JSON 字符串数组返回。",
        },
        "quotes": {
            "label": "引用",
            "format": "引用数组",
            "system": f"从以下文本中提取直接引语和关键陈述（最多 {req.count} 条），以 JSON 字符串数组返回。",
        },
    }

    config = type_config.get(req.extract_type, type_config["keywords"])
    result = client.chat_with_json(
        req.text,
        system=config["system"],
        temperature=0.1,
        max_tokens=2048,
    )

    if result is None:
        # 降级：返回基本结果
        words = [w.strip() for w in req.text[:500].replace("\n", " ").split() if len(w.strip()) > 3][:req.count]
        result = words or ["未提取到有效信息"]

    return _non_stream_response(
        {"extract_type": req.extract_type, "items": result},
        time.time() - t0,
        client.model_key,
    )


# ---- 统计 ----

@router.get("/models")
async def list_available_models():
    """列出可用的 LLM 模型及状态。"""
    return {
        "success": True,
        "data": {
            "models": LLMFactory.list_models(),
        },
    }
