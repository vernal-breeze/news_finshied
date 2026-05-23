"""认证路由：登录、注册、获取当前用户"""
from datetime import timedelta, timezone, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.models.user import User, get_password_hash, verify_password

settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["认证"])

# ---- Schemas ----

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    nickname: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_min_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("用户名至少2个字符")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少6个字符")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}

    @field_validator("role", mode="before")
    @classmethod
    def role_lowercase(cls, v: str) -> str:
        return v.lower()


class UserResponse(BaseModel):
    code: int = 200
    message: str = "ok"
    data: UserOut


# ---- OAuth2 scheme ----

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---- Helpers ----

def _create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def _get_user_from_token(token: str, db: Session) -> User:
    """解析 token 并返回 User，失败则抛 401"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：从请求头 Authorization: Bearer *** 中获取当前用户"""
    return _get_user_from_token(token, db)


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选认证依赖：未提供 token 时返回 None（不抛 401）"""
    if token is None:
        return None
    try:
        return _get_user_from_token(token, db)
    except HTTPException:
        return None


# ---- 路由 ----

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """用户登录，返回 JWT token"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    access_token = _create_token({"sub": user.username})
    return TokenResponse(access_token=access_token)


@router.post("/register", response_model=UserResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名重复
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    user = User(
        username=body.username,
        email=body.email,
        password_hash=get_password_hash(body.password),
        nickname=body.nickname or body.username,
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(data=UserOut.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserResponse(data=UserOut.model_validate(current_user))
