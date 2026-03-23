from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import get_settings

settings = get_settings()

# ──────────────────────────────────────────────────────────────────────────────
# 비동기 엔진 & 세션 팩토리
# ──────────────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,           # DEBUG=true 이면 SQL 로그 출력
    pool_pre_ping=True,            # 끊긴 커넥션 자동 재연결
    pool_size=10,
    max_overflow=20,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # commit 후에도 객체 속성 접근 가능
    autoflush=False,
    autocommit=False,
)


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI Dependency: DB 세션 주입
# ──────────────────────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 엔드포인트에서 아래와 같이 주입하여 사용합니다:

        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Movie))
            ...
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ──────────────────────────────────────────────────────────────────────────────
# 헬스체크용 연결 확인 함수
# ──────────────────────────────────────────────────────────────────────────────
async def check_db_connection() -> bool:
    """DB 연결 상태 확인. 헬스체크 엔드포인트에서 사용."""
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False