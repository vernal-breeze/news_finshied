"""内容路由：AI 生成、润色、摘要、预审等"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/content", tags=["Content"])


class GenerateRequest(BaseModel):
    topic: str
    style: str = "news"
    length: int = 500


class ImproveRequest(BaseModel):
    original_content: str
    improve_type: str = "polish"
    focus_area: Optional[str] = None
    target_length: Optional[int] = None


class AIReviewRequest(BaseModel):
    article_id: Optional[int] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    content: Optional[str] = None


@router.post("/generate")
async def generate(body: GenerateRequest, db: Session = Depends(get_db)):
    return {
        "code": 200,
        "data": {
            "content": f"# {body.topic}\n\n（AI生成功能暂未接入，请配置 AI API Key）\n\n这是一篇关于「{body.topic}」的{body.style}风格稿件，目标长度{body.length}字。"
        },
    }


@router.post("/generate-title")
async def generate_title(body: dict, db: Session = Depends(get_db)):
    return {"code": 200, "data": {"title": "（AI生成标题功能暂未接入）"}}


@router.post("/summarize")
async def summarize(body: dict, db: Session = Depends(get_db)):
    text = body.get("text", "")
    return {"code": 200, "data": {"summary": text[:100] + "…（摘要功能暂未接入）"}}


@router.post("/extract-keywords")
async def extract_keywords(body: dict, db: Session = Depends(get_db)):
    text = body.get("text", "")
    return {"code": 200, "data": {"keywords": text.split()[:5] if text else []}}


@router.post("/evaluate-quality")
async def evaluate_quality(body: dict, db: Session = Depends(get_db)):
    return {"code": 200, "data": {"score": 85.0, "feedback": "质量评估功能暂未接入"}}


@router.post("/improve")
async def improve(body: ImproveRequest, db: Session = Depends(get_db)):
    return {
        "code": 200,
        "data": {
            "content": f"（{body.improve_type}功能暂未接入）\n\n{body.original_content}"
        },
    }


@router.post("/ai-review")
async def ai_review(body: AIReviewRequest, db: Session = Depends(get_db)):
    return {
        "code": 200,
        "data": {
            "result": "pass",
            "comment": "AI预审功能暂未接入，默认通过",
            "score": 80.0,
        },
    }
