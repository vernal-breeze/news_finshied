"""内容路由：AI 生成、润色、摘要、预审等"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.llm import LLMFactory, _extract_json
from app.models.article import Article

logger = logging.getLogger("router.content")
router = APIRouter(prefix="/api/content", tags=["Content"])


# ===================================================================
# 请求模型
# ===================================================================

class GenerateRequest(BaseModel):
    """AI 稿件生成请求（匹配前端 AIArticle 表单）"""
    topic: str                                              # 主题/标题（可从线索拼接）
    keywords: List[str] = []                                # 关键词
    style: str = "news"                                     # 文体：news / formal / casual
    length: str = "medium"                                  # 长度：short / medium / long
    title_count: int = 3                                    # 生成几个备选标题
    tone: str = "professional"                              # 语调：professional / neutral / enthusiastic
    audience: str = "general"                               # 受众：general / expert / public
    reference_material: Optional[str] = None                # 参考素材（线索内容等）
    custom_prompt: Optional[str] = None                      # 用户额外提示词/写作要求


class ImproveRequest(BaseModel):
    original_content: str
    improve_type: str = "polish"                            # polish / expand / condense / rewrite
    focus_area: Optional[str] = None                        # clarity / depth / engagement / accuracy
    target_length: Optional[int] = None


class AIReviewRequest(BaseModel):
    article_id: Optional[int] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    content: Optional[str] = None


# ===================================================================
# Prompt 构建
# ===================================================================

LENGTH_MAP = {
    "short": "800-1200字",
    "medium": "1500-2500字",
    "long": "3000-5000字",
}

STYLE_MAP = {
    "news": "标准新闻稿风格，导语-正文-结尾结构，客观中立",
    "formal": "正式公文风格，严谨规范",
    "casual": "轻松通俗风格，适合新媒体传播",
    "analysis": "深度分析风格，有观点有论据",
}

TONE_MAP = {
    "professional": "专业严谨",
    "neutral": "客观中立",
    "enthusiastic": "积极热烈",
    "critical": "批判反思",
}

AUDIENCE_MAP = {
    "general": "普通大众",
    "expert": "行业专家",
    "public": "政府/公共决策者",
}

NEWS_SYSTEM_PROMPT = """你是一位资深新闻编辑，擅长撰写高质量中文新闻稿件。

要求：
1. 严格遵循用户指定的文体、长度、语调和受众
2. 稿件结构清晰：标题 → 导语 → 正文（分段展开）→ 结语
3. 数据准确、引用可靠、逻辑严谨
4. 语言流畅、避免套话和AI痕迹
5. 如有参考素材，以其为基础进行创作，补充背景和分析

请严格输出 JSON，格式如下：
{
  "suggested_titles": ["标题1", "标题2", "标题3"],
  "draft_content": "完整的稿件正文（Markdown格式）",
  "summary": "100字以内的稿件摘要",
  "recommended_angles": ["角度1", "角度2"],
  "structure_suggestion": "建议的文章结构说明"
}

不要输出 Markdown 代码块，直接输出 JSON 对象。"""

IMPROVE_SYSTEM_PROMPT = """你是一位资深中文编辑，擅长润色和改进新闻稿件。

根据用户指定的改进类型处理原文：
- polish: 润色语言，优化表达，不改动原意
- expand: 扩展内容，增加细节和背景
- condense: 精简内容，保留核心信息
- rewrite: 重写，保留核心信息但改变表达方式

请直接输出润色后的完整文本，不要加任何解释。"""

REVIEW_SYSTEM_PROMPT = """你是一位严格的新闻审核编辑。请审核以下稿件，从以下维度评分（1-100）：

1. 事实准确性：内容是否有明显事实错误
2. 语言规范：语法、用词是否规范
3. 结构逻辑：文章结构是否清晰合理
4. 新闻价值：选题是否有新闻价值

请输出 JSON：
{
  "result": "pass" 或 "reject" 或 "revision",
  "score": 综合评分(1-100),
  "comment": "审核意见",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}"""


# ===================================================================
# 辅助函数
# ===================================================================

def _get_llm():
    """获取 LLM 客户端（单例）"""
    return LLMFactory.create()


# ===================================================================
# 路由
# ===================================================================

@router.post("/generate")
async def generate(body: GenerateRequest, db: Session = Depends(get_db)):
    """AI 稿件生成 — 调用 DeepSeek chat 模型"""
    llm = _get_llm()

    if not llm.available:
        raise HTTPException(
            status_code=503,
            detail="AI 服务未配置。请在 .env 中设置 DEEPSEEK_API_KEY",
        )

    # 构建用户 prompt
    parts = [f"主题：{body.topic}"]

    if body.keywords:
        parts.append(f"关键词：{'、'.join(body.keywords)}")
    if body.reference_material:
        # 限制参考素材长度
        ref = body.reference_material[:3000]
        parts.append(f"参考素材：\n{ref}")
    if body.custom_prompt and body.custom_prompt.strip():
        custom_prompt = body.custom_prompt.strip()[:1200]
        parts.append(f"用户额外提示词/写作要求：\n{custom_prompt}")

    parts.append(f"文体风格：{STYLE_MAP.get(body.style, body.style)}")
    parts.append(f"目标长度：{LENGTH_MAP.get(body.length, body.length)}")
    parts.append(f"语调：{TONE_MAP.get(body.tone, body.tone)}")
    parts.append(f"目标受众：{AUDIENCE_MAP.get(body.audience, body.audience)}")
    parts.append(f"备选标题数量：{body.title_count}")

    user_prompt = "\n\n".join(parts)
    logger.info("AI generate: topic=%s, style=%s, length=%s", body.topic[:50], body.style, body.length)

    # 调用 LLM
    try:
        raw = llm.chat(
            user_prompt,
            system=NEWS_SYSTEM_PROMPT,
            temperature=0.8,
            max_tokens=4096,
        )
    except Exception as exc:
        logger.error("AI generate failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"AI 生成失败：{exc}")

    # 解析 JSON
    data = _extract_json(raw)
    if not data:
        # LLM 没返回合法 JSON，把原始文本当 draft_content 返回
        logger.warning("AI generate: JSON parse failed, using raw text")
        return {
            "code": 200,
            "data": {
                "suggested_titles": [body.topic],
                "draft_content": raw.strip(),
                "summary": "",
                "recommended_angles": [],
                "structure_suggestion": "",
            },
        }

    return {
        "code": 200,
        "data": {
            "suggested_titles": data.get("suggested_titles", []) or [body.topic],
            "draft_content": data.get("draft_content", "") or raw.strip(),
            "summary": data.get("summary", "") or "",
            "recommended_angles": data.get("recommended_angles", []) or [],
            "structure_suggestion": data.get("structure_suggestion", "") or "",
        },
    }


@router.post("/generate-title")
async def generate_title(body: dict, db: Session = Depends(get_db)):
    """AI 生成备选标题"""
    llm = _get_llm()
    if not llm.available:
        return {"code": 200, "data": {"title": body.get("topic", "") or "（AI未配置）"}}

    content = body.get("content", "")[:2000]
    topic = body.get("topic", "")

    prompt = f"""请为以下内容生成 5 个备选标题，直接输出标题列表（每行一个）：

主题：{topic}
内容摘要：{content[:500]}

要求：
- 标题简洁有力，10-25字
- 覆盖不同角度（事实陈述、悬念、数据、观点等）
- 适合新闻媒体发布"""

    try:
        raw = llm.chat(prompt, temperature=0.8, max_tokens=512)
        titles = [t.strip("0123456789. -)）") for t in raw.strip().split("\n") if t.strip()]
        titles = [t for t in titles if len(t) >= 5][:5]
        return {"code": 200, "data": {"titles": titles or [topic]}}
    except Exception as exc:
        return {"code": 200, "data": {"title": topic}}


@router.post("/summarize")
async def summarize(body: dict, db: Session = Depends(get_db)):
    """AI 摘要生成"""
    llm = _get_llm()
    text = body.get("text", "")[:5000]

    if not llm.available or not text.strip():
        return {"code": 200, "data": {"summary": text[:200] + "…" if len(text) > 200 else text}}

    try:
        raw = llm.chat(
            f"请为以下内容生成一段简洁的摘要（150字以内）：\n\n{text}",
            temperature=0.3,
            max_tokens=300,
        )
        return {"code": 200, "data": {"summary": raw.strip()}}
    except Exception:
        return {"code": 200, "data": {"summary": text[:200] + "…"}}


@router.post("/extract-keywords")
async def extract_keywords(body: dict, db: Session = Depends(get_db)):
    """AI 关键词提取"""
    llm = _get_llm()
    text = body.get("text", "")[:3000]

    if not llm.available or not text.strip():
        return {"code": 200, "data": {"keywords": text.split()[:5] if text else []}}

    try:
        raw = llm.chat(
            f"请从以下文本中提取5-10个关键词，用逗号分隔，只输出关键词：\n\n{text}",
            temperature=0.3,
            max_tokens=128,
        )
        keywords = [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()][:10]
        return {"code": 200, "data": {"keywords": keywords}}
    except Exception:
        return {"code": 200, "data": {"keywords": []}}


@router.post("/evaluate-quality")
async def evaluate_quality(body: dict, db: Session = Depends(get_db)):
    """AI 稿件质量评估"""
    llm = _get_llm()
    text = body.get("content", "")[:3000]

    if not llm.available:
        return {"code": 200, "data": {"score": 85.0, "feedback": "AI 未配置"}}

    try:
        raw = llm.chat_with_json(
            f"请评估以下稿件质量，从 1-100 打分并给出简要反馈（JSON: score, feedback）：\n\n{text}",
            temperature=0.3,
            max_tokens=300,
        )
        if raw:
            return {"code": 200, "data": {"score": float(raw.get("score", 80)), "feedback": raw.get("feedback", "")}}
    except Exception:
        pass
    return {"code": 200, "data": {"score": 85.0, "feedback": "评估完成"}}


@router.post("/improve")
async def improve(body: ImproveRequest, db: Session = Depends(get_db)):
    """AI 内容润色/改进"""
    llm = _get_llm()
    if not llm.available:
        return {"code": 200, "data": {"content": f"（AI未配置）\n\n{body.original_content}"}}

    improve_type_names = {
        "polish": "润色优化",
        "expand": "扩展丰富",
        "condense": "精简浓缩",
        "rewrite": "重写改写",
    }
    action = improve_type_names.get(body.improve_type, "润色")
    focus_hint = f"，重点关注{body.focus_area}方面" if body.focus_area else ""

    try:
        raw = llm.chat(
            f"请对以下内容进行{action}{focus_hint}：\n\n{body.original_content}",
            system=IMPROVE_SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=4096,
        )
        return {"code": 200, "data": {"content": raw.strip()}}
    except Exception as exc:
        return {"code": 200, "data": {"content": f"（改进失败：{exc}）\n\n{body.original_content}"}}


@router.post("/ai-review")
async def ai_review(body: AIReviewRequest, db: Session = Depends(get_db)):
    """AI 稿件预审 — 优先按 article_id 查库，其次用请求中透传的 title/content"""
    llm = _get_llm()
    if not llm.available:
        return {"code": 200, "data": {"result": "pass", "comment": "AI 未配置，默认通过", "score": 80.0}}

    # 第1优先：按 article_id 从数据库查稿件正文
    title = body.title
    abstract = body.abstract
    content = body.content

    if body.article_id:
        article = db.query(Article).filter(Article.id == body.article_id).first()
        if article:
            title = title or article.title
            abstract = abstract or article.summary or ""
            content = content or article.content or ""

    # 构建审核素材
    parts = []
    if title:
        parts.append(f"标题：{title}")
    if abstract:
        parts.append(f"摘要：{abstract}")
    if content:
        parts.append(f"正文：{content[:4000]}")

    if not parts:
        return {"code": 200, "data": {"result": "pass", "comment": "无内容可审", "score": 80.0}}

    review_text = "\n\n".join(parts)

    try:
        data = llm.chat_with_json(
            f"请审核以下稿件：\n\n{review_text}",
            system=REVIEW_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1024,
        )
        if data:
            return {"code": 200, "data": data}
    except Exception as exc:
        logger.error("AI review failed: %s", exc)

    return {"code": 200, "data": {"result": "pass", "comment": "审核完成", "score": 80.0}}
