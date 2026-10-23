"""운영자 계정 시드. ADMIN_EMAIL / ADMIN_PASSWORD 환경변수를 읽는다.

    uv run python -m app.seed
"""
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Operator
from app.security import hash_password


def main() -> None:
    s = get_settings()
    with SessionLocal() as db:
        email = s.admin_email.lower()
        if db.scalar(select(Operator).where(Operator.email == email)):
            print(f"이미 존재하는 운영자: {email}")
            return
        db.add(Operator(email=email, password_hash=hash_password(s.admin_password)))
        db.commit()
        print(f"운영자 생성: {email}")


if __name__ == "__main__":
    main()
