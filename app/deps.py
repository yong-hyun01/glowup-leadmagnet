from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Operator
from app.security import SESSION_COOKIE, read_session_token


def get_current_operator(request: Request, db: Session = Depends(get_db)) -> Operator:
    token = request.cookies.get(SESSION_COOKIE)
    operator_id = read_session_token(token) if token else None
    operator = db.get(Operator, operator_id) if operator_id else None
    if operator is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")
    return operator


def get_optional_operator(request: Request, db: Session = Depends(get_db)) -> Operator | None:
    token = request.cookies.get(SESSION_COOKIE)
    operator_id = read_session_token(token) if token else None
    return db.get(Operator, operator_id) if operator_id else None
