"""用户个人中心 API"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, get_password_hash, verify_password
from app.models.article import Article
from app.models.review import Review
from app.models.clue import Clue
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
