"""系统设置 API — 仅管理员/主编可修改"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])

# 设置文件路径
_SETTINGS_FILE = Path(__file__).resolve().parents[3] / "config" / "system_settings.json"

# 默认系统设置
_DEFAULTS = {
    "site_name": "新闻内容采编系统",
    "logo_url": "",
    "copyright": f"© 2025 News Editor System. All rights reserved.",
    "favicon_url": "",
    "description": "专业的新闻内容采编与审核平台",
    "allow_registration": True,
    "require_ai_check": True,
    "email_notification": True,
    "review_timeout_hours": 24,
    "min_word_count": 500,
}


def _load_settings() -> dict:
    """从文件加载设置，不存在则用默认值"""
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并保存的值与默认值（确保新字段有值）
            return {**_DEFAULTS, **saved}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULTS)


def _save_settings(data: dict) -> None:
    """保存设置到文件"""
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _is_admin_or_chief(user: User) -> bool:
    return user.role in ("admin", "chief_editor")


@router.get("")
def get_settings():
    """获取系统设置（公开可读）"""
    return {"code": 200, "data": _load_settings()}


class SettingsUpdate(BaseModel):
    site_name: Optional[str] = None
    logo_url: Optional[str] = None
    copyright: Optional[str] = None
    favicon_url: Optional[str] = None
    description: Optional[str] = None
    allow_registration: Optional[bool] = None
    require_ai_check: Optional[bool] = None
    email_notification: Optional[bool] = None
    review_timeout_hours: Optional[int] = None
    min_word_count: Optional[int] = None


@router.put("")
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """更新系统设置（仅管理员/主编）"""
    if not _is_admin_or_chief(current_user):
        raise HTTPException(status_code=403, detail="仅管理员或主编可修改系统设置")

    current = _load_settings()
    updates = body.model_dump(exclude_none=True)
    current.update(updates)
    _save_settings(current)

    return {"code": 200, "message": "系统设置已更新", "data": current}
