from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..auth import COOKIE_NAME, create_access_token, get_current_user, hash_password, verify_password
from ..config import settings
from ..db import get_db
from ..models import User, UserRole, UserStatus

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    status: str

    class Config:
        from_attributes = True


def _to_user_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), email=user.email, role=user.role.value, status=user.status.value)


def _set_auth_cookie(response: Response, user_id: str) -> None:
    token = create_access_token(user_id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_days * 24 * 3600,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Senha precisa ter pelo menos 8 caracteres")
    existing = db.query(User).filter(User.email == req.email.lower()).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Já existe um cadastro com esse email")
    user = User(
        email=req.email.lower(),
        password_hash=hash_password(req.password),
        role=UserRole.user,
        status=UserStatus.pending,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@router.post("/login", response_model=UserOut)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).one_or_none()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if user.status == UserStatus.pending:
        raise HTTPException(status_code=403, detail="Seu cadastro ainda está aguardando aprovação")
    if user.status == UserStatus.rejected:
        raise HTTPException(status_code=403, detail="Seu cadastro não foi aprovado")
    _set_auth_cookie(response, str(user.id))
    return _to_user_out(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _to_user_out(user)
