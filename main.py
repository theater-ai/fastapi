from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import router # API 라우터
from src.api.chat import router as chat_router # Chat API 라우터
from src.core.config import get_settings
from src.core.database import check_db_connection

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    서버 시작 시 DB 연결 확인 → 로그 출력.
    실제 DB 연결 풀은 첫 요청 시점에 생성되므로, 여기서는 단순히 연결 가능 여부만 체크
    서버 종료 시 로그 출력.
    """
    print(f"{settings.APP_TITLE} v{settings.APP_VERSION} starting up...")
    connected = await check_db_connection()
    print("DB connection established" if connected else "DB connection failed")
    yield
    print("server shutting down...")


# FastAPI 애플리케이션 생성 및 설정
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS 설정 (개발 편의 위해 모든 출처 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(router)
app.include_router(chat_router)

@app.get("/health", tags=["System"])
async def health_check():
    db_ok = await check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "unreachable",
        "version": settings.APP_VERSION,
    }