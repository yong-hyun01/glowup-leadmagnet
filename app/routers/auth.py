from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_operator
from app.models import Operator
from app.schemas import LoginRequest, OperatorOut
from app.security import SESSION_COOKIE, create_session_token, verify_password

router = APIRouter(prefix="/admin/api/auth", tags=["auth"])

# 관리자 세션 쿠키는 /admin 경로에만 전송되고(SameSite=Strict, HttpOnly),
# 공개 폼(/f, /l, /public) 과 sandbox iframe 에서는 절대 전달되지 않는다.
COOKIE_PATH = "/admin"


def set_session_cookie(response: Response, operator_id: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(operator_id),
        max_age=settings.session_max_age_seconds,
        path=COOKIE_PATH,
        httponly=True,
        samesite="strict",
        secure=settings.app_env == "production",
    )


@router.post("/login", response_model=OperatorOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    operator = db.scalar(select(Operator).where(Operator.email == body.email.lower()))
    if operator is None or not verify_password(body.password, operator.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    set_session_cookie(response, operator.id)
    return operator


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path=COOKIE_PATH)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=OperatorOut)
def me(operator: Operator = Depends(get_current_operator)):
    return operator
