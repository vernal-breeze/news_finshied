"""用户个人中心 API"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, get_password_hash, verify_password
from app.models.article import Article
from app.models.review import Review
from app.models.clue import Clue
from app.models.message import Message
from app.models.topic import Topic
from app.routers.auth import get_current_user
from app.routers.public import UPLOAD_DIR

router = APIRouter(prefix="/api/users", tags=["Users"])


class ProfileResponse(BaseModel):
    """个人中心响应"""
    id: int
    username: str
    nickname: str
    email: str
    role: str
    avatar: str
    full_name: str
    created_at: str
    updated_at: str
    # 统计数据
    article_count: int = 0        # 总稿件
    published_count: int = 0      # 已发布
    pending_review_count: int = 0 # 待审核
    clue_count: int = 0           # 线索总数
    # 最近活动
    last_login: Optional[str] = None


class ProfileUpdate(BaseModel):
    """个人信息更新"""
    nickname: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class PasswordUpdate(BaseModel):
    """密码修改"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=50)


class AdminPasswordReset(BaseModel):
    """管理员重置人员密码"""
    new_password: str = Field(..., min_length=6, max_length=50)


ROLE_LABELS = {
    "admin": "管理员",
    "chief_editor": "主编",
    "editor": "编辑",
    "reviewer": "审核员",
    "reporter": "记者",
    "user": "投稿用户",
}


def _ensure_admin(user: User) -> None:
    """管理员端接口权限校验。"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可访问")


def _serialize_admin_user(user: User, db: Session) -> dict:
    """管理员人员列表中的用户摘要。"""
    article_query = db.query(Article).filter(Article.author_id == user.id)
    review_query = db.query(Review).filter(Review.reviewer_id == user.id)
    clue_query = db.query(Clue).filter(Clue.creator_id == user.id)

    article_count = article_query.count()
    published_count = article_query.filter(Article.status == "published").count()
    pending_review_count = article_query.filter(
        Article.status.in_(["pending_review", "reviewing"])
    ).count()
    draft_count = article_query.filter(Article.status == "draft").count()

    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname or user.username,
        "full_name": user.full_name or "",
        "email": user.email,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "is_active": bool(user.is_active),
        "avatar": user.avatar or "",
        "created_at": user.created_at.isoformat() if user.created_at else "",
        "updated_at": user.updated_at.isoformat() if user.updated_at else "",
        "article_count": article_count,
        "published_count": published_count,
        "pending_review_count": pending_review_count,
        "draft_count": draft_count,
        "review_count": review_query.count(),
        "clue_count": clue_query.count(),
    }


@router.get("/me")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取当前用户个人信息和统计数据"""
    # 统计稿件数量（管理员显示全站统计，其他角色显示个人统计）
    if current_user.role == "admin":
        article_count = db.query(Article).count()
        published_count = db.query(Article).filter(Article.status == "published").count()
    else:
        article_count = db.query(Article).filter(Article.author_id == current_user.id).count()
        published_count = db.query(Article).filter(
            Article.author_id == current_user.id, Article.status == "published"
        ).count()
    # 统计审核数量
    review_count = db.query(Review).filter(Review.reviewer_id == current_user.id).count()

    # 待审核数与线索总数（管理员显示全站，其他显示个人统计）
    if current_user.role == "admin":
        pending_review_count = db.query(Article).filter(
            Article.status.in_(["pending_review", "reviewing"])
        ).count()
        clue_count = db.query(Clue).count()
    else:
        pending_review_count = review_count  # 非管理员显示自己的审核数
        clue_count = 0

    return {
        "code": 200,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "nickname": current_user.nickname or current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "avatar": current_user.avatar or "",
            "full_name": current_user.full_name or "",
            "created_at": current_user.created_at.isoformat() if current_user.created_at else "",
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else "",
            "article_count": article_count,
            "published_count": published_count,
            "pending_review_count": pending_review_count,
            "clue_count": clue_count,
            "last_login": current_user.updated_at.isoformat() if current_user.updated_at else "",
        }
    }


@router.get("/admin/overview")
def get_admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员控制台概览：系统数据、角色分布、内容状态。"""
    _ensure_admin(current_user)

    since = datetime.now(timezone.utc) - timedelta(days=7)

    role_rows = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    role_counts = {role or "unknown": count for role, count in role_rows}
    article_status_rows = (
        db.query(Article.status, func.count(Article.id))
        .group_by(Article.status)
        .all()
    )
    article_status = {status or "unknown": count for status, count in article_status_rows}

    total_articles = db.query(Article).count()
    total_clues = db.query(Clue).count()
    total_reviews = db.query(Review).count()
    total_views = db.query(func.sum(Article.view_count)).scalar() or 0
    total_likes = db.query(func.sum(Article.like_count)).scalar() or 0

    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    inactive_users = db.query(User).filter(User.is_active.is_(False)).count()

    recent_users = (
        db.query(User)
        .order_by(desc(User.created_at))
        .limit(5)
        .all()
    )

    return {
        "code": 200,
        "data": {
            "users": {
                "total": db.query(User).count(),
                "active": active_users,
                "inactive": inactive_users,
                "by_role": [
                    {
                        "role": role,
                        "label": ROLE_LABELS.get(role, role),
                        "count": count,
                    }
                    for role, count in sorted(role_counts.items())
                ],
                "reviewers": role_counts.get("reviewer", 0),
                "reporters": role_counts.get("reporter", 0) + role_counts.get("user", 0),
                "editors": role_counts.get("editor", 0) + role_counts.get("chief_editor", 0),
            },
            "content": {
                "articles": total_articles,
                "clues": total_clues,
                "reviews": total_reviews,
                "published": article_status.get("published", 0),
                "draft": article_status.get("draft", 0),
                "pending_review": article_status.get("pending_review", 0)
                + article_status.get("reviewing", 0),
                "recent_articles_7days": db.query(Article).filter(Article.created_at >= since).count(),
                "recent_clues_7days": db.query(Clue).filter(Clue.created_at >= since).count(),
            },
            "traffic": {
                "views": int(total_views),
                "likes": int(total_likes),
            },
            "recent_users": [_serialize_admin_user(user, db) for user in recent_users],
        },
    }


@router.get("/admin/users")
def list_admin_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[str] = None,
    roles: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员查看人员列表，支持按角色、状态、关键词筛选。"""
    _ensure_admin(current_user)

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    q = db.query(User)

    role_list = [item.strip() for item in (roles or "").split(",") if item.strip()]
    if role_list:
        q = q.filter(User.role.in_(role_list))
    elif role:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active.is_(is_active))
    if search:
        kw = f"%{search.strip()}%"
        q = q.filter(
            or_(
                User.username.ilike(kw),
                User.nickname.ilike(kw),
                User.full_name.ilike(kw),
                User.email.ilike(kw),
            )
        )

    total = q.count()
    users = (
        q.order_by(desc(User.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "code": 200,
        "data": [_serialize_admin_user(user, db) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/admin/users/{user_id}")
def delete_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员删除人员账号；保留业务数据并清空人员引用。"""
    _ensure_admin(current_user)

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
    if target_user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="至少需要保留一个管理员账号")

    cleanup_counts = {
        "articles": db.query(Article)
        .filter(Article.author_id == target_user.id)
        .update({Article.author_id: None}, synchronize_session=False),
        "reviews": db.query(Review)
        .filter(Review.reviewer_id == target_user.id)
        .update({Review.reviewer_id: None}, synchronize_session=False),
        "clues": db.query(Clue)
        .filter(Clue.creator_id == target_user.id)
        .update({Clue.creator_id: None}, synchronize_session=False),
        "topics_editor": db.query(Topic)
        .filter(Topic.editor_id == target_user.id)
        .update({Topic.editor_id: None}, synchronize_session=False),
        "topics_assigned": db.query(Topic)
        .filter(Topic.assigned_user_id == target_user.id)
        .update({Topic.assigned_user_id: None}, synchronize_session=False),
        "messages": db.query(Message)
        .filter(Message.recipient_id == target_user.id)
        .update({Message.recipient_id: None}, synchronize_session=False),
    }

    deleted_user = {
        "id": target_user.id,
        "username": target_user.username,
        "role": target_user.role,
    }
    db.delete(target_user)
    db.commit()

    return {
        "code": 200,
        "message": "人员账号已删除，历史业务数据已保留",
        "data": {
            "deleted_user": deleted_user,
            "cleanup_counts": cleanup_counts,
        },
    }


@router.put("/admin/users/{user_id}/password")
def reset_admin_user_password(
    user_id: int,
    body: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员重置人员账号密码。"""
    _ensure_admin(current_user)

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="当前管理员请在个人中心修改自己的密码")
    if target_user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员账号密码请由本人修改")

    target_user.password_hash = get_password_hash(body.new_password)
    target_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"code": 200, "message": "人员密码已重置"}


@router.put("/me")
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """更新个人信息"""
    if body.nickname is not None:
        current_user.nickname = body.nickname
    if body.email is not None:
        # 检查邮箱唯一性
        existing = db.query(User).filter(User.email == body.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已被其他用户使用")
        current_user.email = body.email
    if body.full_name is not None:
        current_user.full_name = body.full_name

    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)

    return {
        "code": 200,
        "message": "个人信息更新成功",
        "data": {
            "id": current_user.id,
            "nickname": current_user.nickname,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "avatar": current_user.avatar or "",
        }
    }


@router.put("/me/password")
def update_password(body: PasswordUpdate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """修改密码"""
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    current_user.password_hash = get_password_hash(body.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"code": 200, "message": "密码修改成功"}


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    """上传/更新头像（最大 2MB）"""
    # 校验文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    # 读取并限制大小
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像文件不能超过 2MB")

    # 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    filename = f"avatar_{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
    filepath = UPLOAD_DIR / filename

    # 保存文件
    with open(filepath, "wb") as f:
        f.write(contents)

    # 更新用户头像
    url = f"/uploads/{filename}"
    current_user.avatar = url
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"code": 200, "message": "头像上传成功", "data": {"url": url}}
