#!/usr/bin/env python3
"""
数据库初始化工具 - 一键管理数据库生命周期

用法（可从任意目录执行）:
    python database_init/database_init.py --drop
    python database_init/database_init.py --create
    python database_init/database_init.py --seed
    python database_init/database_init.py --all

注意：
    - 脚本会自动定位 backend/ 目录，无需手动 cd
    - --drop 会删除所有数据，不可恢复！
    - --seed 依赖 Faker 库：pip install faker bcrypt
"""

import sys
import os
from pathlib import Path


def _setup_project_path():
    """确保 CWD 在 backend/ 目录，并设置 sys.path，创建必要的数据目录"""
    # 找到 backend/ 目录（本脚本在 backend/database_init/ 下）
    script_dir = Path(__file__).resolve().parent          # database_init/
    backend_dir = script_dir.parent                        # backend/
    
    # 切换到 backend/ 目录（让 .env 和 ./data/ 路径正确解析）
    os.chdir(str(backend_dir))
    
    # 将 backend/ 加入 sys.path（确保 app.* 可导入）
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    # 确保 data/ 目录存在（SQLite 模式需要，MySQL 模式无害）
    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return backend_dir


# ── 必须在任何 app.* 导入之前调用 ──
_backend_dir = _setup_project_path()

from app.database import engine
from app.models.base import Base


def drop_all_tables():
    """删除所有表（保留数据库连接）"""
    print("=" * 60)
    print("[DROP] 正在删除所有表...")
    Base.metadata.drop_all(bind=engine)
    print("[DROP] ✅ 所有表已删除")
    print("=" * 60)


def create_all_tables():
    """创建所有模型对应的表"""
    # 导入所有模型以确保它们注册到 Base.metadata
    import app.models.user       # noqa: F401
    import app.models.article    # noqa: F401
    import app.models.clue       # noqa: F401
    import app.models.topic      # noqa: F401
    import app.models.review     # noqa: F401
    import app.models.feedback   # noqa: F401
    import app.models.message    # noqa: F401
    import app.models.collection # noqa: F401

    print("=" * 60)
    print("[CREATE] 正在创建所有表...")
    Base.metadata.create_all(bind=engine)
    print("[CREATE] ✅ 所有表已创建")
    print("=" * 60)


def seed_test_data():
    """生成测试数据"""
    from database_init.database_insertdata import run_seed
    run_seed()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="数据库初始化工具 - 管理数据库表结构与测试数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    cd backend
    python database_init/database_init.py --drop      # 清空所有表
    python database_init/database_init.py --create    # 建表
    python database_init/database_init.py --seed      # 生成测试数据
    python database_init/database_init.py --all       # 一键重建（drop + create + seed）
        """
    )
    parser.add_argument("--drop", action="store_true", help="清空所有表")
    parser.add_argument("--create", action="store_true", help="创建所有表")
    parser.add_argument("--seed", action="store_true", help="生成测试数据")
    parser.add_argument("--all", action="store_true", help="一键执行 drop + create + seed")

    args = parser.parse_args()

    # --all 等价于 --drop --create --seed
    if args.all:
        args.drop = True
        args.create = True
        args.seed = True

    if not any([args.drop, args.create, args.seed]):
        parser.print_help()
        return

    try:
        if args.drop:
            drop_all_tables()

        if args.create:
            create_all_tables()

        if args.seed:
            # drop + create 之后才 seed
            if not args.drop and not args.create:
                print("[WARN] 建议先 --create 建表再 --seed")
            seed_test_data()

        print("\n🎉 操作完成！")
    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
