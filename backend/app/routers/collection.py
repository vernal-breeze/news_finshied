"""采集任务路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.collection import Collection
from app.models.clue import Clue
from app.schemas.base import BaseResponse, DataResponse, PaginationResponse, create_data_response, create_pagination_response

# 使用单数 /api/collection 匹配前端 API 调用
router = APIRouter(prefix="/api/collection", tags=["Collection"])


@router.get("/tasks", response_model=PaginationResponse, summary="获取采集任务列表")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """分页获取采集任务列表，支持按状态筛选"""
    query = db.query(Collection)
    if status:
        query = query.filter(Collection.status == status)
    
    total = query.count()
    tasks = (
        query.order_by(desc(Collection.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return create_pagination_response(
        data=[
            {
                "id": t.id,
                "name": t.name,
                "keywords": t.keywords,
                "channels": t.channels,
                "status": t.status,
                "result_count": t.result_count,
                "error_msg": t.error_msg,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/tasks", response_model=DataResponse, summary="创建采集任务")
async def create_task(
    body: dict,
    db: Session = Depends(get_db),
):
    """创建新的采集任务"""
    task = Collection(
        name=body.get("name", ""),
        keywords=body.get("keywords", ""),
        channels=body.get("channels", "ithome,36kr"),
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return create_data_response(
        data={
            "id": task.id,
            "name": task.name,
            "keywords": task.keywords,
            "channels": task.channels,
            "status": task.status,
            "result_count": task.result_count,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
    )


@router.get("/materials", response_model=PaginationResponse, summary="获取采集素材列表")
async def list_materials(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """分页获取采集到的素材（新闻线索）"""
    query = db.query(Clue)
    if keyword:
        query = query.filter(
            Clue.title.ilike(f"%{keyword}%") |
            Clue.keywords.ilike(f"%{keyword}%")
        )
    if source:
        query = query.filter(Clue.source.ilike(f"%{source}%"))
    
    total = query.count()
    materials = (
        query.order_by(desc(Clue.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return create_pagination_response(
        data=[
            {
                "id": m.id,
                "title": m.title,
                "url": m.source_url or '',
                "source": m.source,
                "category": m.category,
                "keywords": m.keywords,
                "news_value": m.news_value_score or 0,
                "propagation_potential": m.propagation_potential or 0,
                "status": m.status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in materials
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
