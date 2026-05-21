#!/usr/bin/env python3
"""
一键建表工具 - 创建所有模型对应的数据库表

用法（可从任意目录执行）:
    python database_init/database_createtable.py

说明:
    - 脚本会自动定位 backend/ 目录，无需手动 cd
    - 导入所有 ORM 模型使其注册到 Base.metadata
    - 调用 create_all() 在数据库中创建相应的表
    - 已存在的表不会被重复创建
"""

import sys
import os
from pathlib import Path


def _setup_project_path():
    """确保 CWD 在 backend/ 目录，并设置 sys.path，创建必要的数据目录"""
    script_dir = Path(__file__).resolve().parent          # database_init/
    backend_dir = script_dir.parent                        # backend/

    os.chdir(str(backend_dir))

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    return backend_dir


# ── 必须在任何 app.* 导入之前调用 ──
_backend_dir = _setup_project_path()

from app.database import engine
from app.models.base import Base

# ── 导入所有模型（触发注册到 Base.metadata） ──
import app.models.user       # noqa: F401  - User
import app.models.article    # noqa: F401  - Article
import app.models.clue       # noqa: F401  - Clue
import app.models.topic      # noqa: F401  - Topic
import app.models.review     # noqa: F401  - Review
import app.models.feedback   # noqa: F401  - Feedback
import app.models.message    # noqa: F401  - Message
import app.models.collection # noqa: F401  - Collection


def create_all():
    """创建所有表"""
    print("=" * 60)
    print("[CREATE] 正在创建所有表...")
    print(f"[CREATE] 数据库引擎: {engine.url}")
    print(f"[CREATE] 工作目录:   {os.getcwd()}")
    print()
    Base.metadata.create_all(bind=engine)

    tables = Base.metadata.tables.keys()
    print(f"\n[CREATE] ✅ 已就绪 {len(tables)} 张表:")
    for name in sorted(tables):
        print(f"         - {name}")
    print("=" * 60)


if __name__ == "__main__":
    create_all()
