import os
from fastapi import Header, HTTPException, status

INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "only-from-spring")

def verify_internal(x_internal_secret: str = Header(...)):
    """Spring 게이트웨이를 통한 내부 요청만 허용"""
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="외부에서 직접 접근할 수 없습니다."
        )

def get_current_user_email(x_user_email: str = Header(...)) -> str:
    """Spring이 전달한 인증된 사용자 이메일 추출"""
    if not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자 정보가 없습니다."
        )
    return x_user_email
