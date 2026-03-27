from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.deps import verify_internal, get_current_user_email
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.response import (
    BoxofficeRowOut,
    CreditOut,
    DashboardOut,
    MovieSummaryOut,
    ScrapeOut,
    SearchOut,
)
from src.core.database import get_db
from src.service.movie import MovieService
from src.service.scrape import ScrapeService
from src.external.kobis import KobisClient

"""
영화 API 엔드포인트
- GET  /movies/search?q={title} → 영화 제목 검색
- POST /movies/scrape?title={title} → KOBIS API + 스크래핑 → DB 적재
- GET  /movies/{movie_cd}/dashboard → 영화 대시보드 데이터 조회
"""

# API 라우터 정의
# tags=['Movies'] → Swagger UI에서 엔드포인트 그룹화
router = APIRouter(prefix="/movies", tags=["Movies"])

# 서비스 인스턴스 (싱글톤으로 재사용)
_movie_svc = MovieService()
_scrape_svc = ScrapeService()
_kobis_client = KobisClient()


# --------------------------------------------- ENDPOINT ---------------------------------------------

@router.get("/search", response_model=SearchOut, summary="영화 DB 검색")
async def search_movies(
    q: str = Query(..., min_length=1, description="검색할 영화 제목"),
    # user_email: str = Depends(get_current_user_email), 잠시
    db: AsyncSession = Depends(get_db),
) -> SearchOut:
    """
    제목(한글/영문) LIKE 검색. 최대 20건 반환.
    param
    - q: 검색어 (필수, 최소 1자)
    - db: DB 세션 (의존성 주입)
    returns:
    - query: 검색어
    - count: 검색 결과 수
    - results: 영화 요약 정보 리스트
    """
    movies = await _movie_svc.search(db, q)
    return SearchOut(
        query=q,
        count=len(movies),
        results=[MovieSummaryOut.model_validate(m) for m in movies],
    )


@router.post(
    "/scrape",
    response_model=ScrapeOut,
    status_code=status.HTTP_201_CREATED,
    summary="영화 스크래핑 및 DB 적재",
)
async def scrape_movie(
    title: str = Query(..., min_length=1, description="스크래핑할 영화 제목"),
    db: AsyncSession = Depends(get_db),
    # user_email: str = Depends(get_current_user_email), 잠시
) -> ScrapeOut:
    """
    주어진 영화 제목으로 스크래핑하고 DB에 적재합니다.
    param
        title: 스크래핑할 영화 제목 (필수, 최소 1자)
        db: DB 세션 (의존성 주입)
    returns:
        ScrapeOut: 스크래핑 결과
    """
    try:
        movie, bo_count = await _scrape_svc.scrape_and_save(db, title)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"스크래핑 중 오류가 발생했습니다: {e}",
        )

    return ScrapeOut(
        movie_cd=movie.movie_cd,
        movie_nm=movie.movie_nm,
        boxoffice_rows=bo_count,
        message=f"'{movie.movie_nm}' 박스오피스 {bo_count}건 적재 완료",
    )


@router.get(
    "/{movie_cd}/dashboard",
    response_model=DashboardOut,
    summary="영화 대시보드 데이터 조회",
)
async def get_dashboard(
    movie_cd: str,
    date_from: Optional[date] = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    # user_email: str = Depends(get_current_user_email), 잠시
) -> DashboardOut:
    """
    영화 대시보드 데이터 조회
    params:
    - movie_cd: 영화 코드 (필수)
    - date_from: 조회 시작일 (선택, YYYY-MM-DD)
    - date_to: 조회 종료일 (선택, YYYY-MM-DD)
    returns:
    - movie: 영화 상세 정보
    - directors: 감독 정보 리스트
    - actors: 배우 정보 리스트
    - boxoffice: 박스오피스 시계열 데이터 리스트
    - total_audi: 누적 관객 수
    - total_sales: 누적 매출액
    - peak_audi_date: 관객 수 최고일
    - peak_sales_date: 매출액 최고일
    """

    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from은 date_to보다 이전이어야 합니다.",
        )

    try:
        result = await _movie_svc.get_dashboard(db, movie_cd, date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return DashboardOut(
        movie=MovieSummaryOut.model_validate(result.movie),
        directors=[CreditOut.model_validate(c) for c in result.directors],
        actors=[CreditOut.model_validate(c) for c in result.actors],
        boxoffice=[BoxofficeRowOut.model_validate(b) for b in result.boxoffice],
        total_audi=result.total_audi,
        total_sales=result.total_sales,
        peak_audi_date=result.peak_audi_date,
        peak_sales_date=result.peak_sales_date,
    )

@router.get("/suggest", summary="채팅창 @ 멘션용 영화 실시간 자동완성")
async def suggest_movies(
    q: str = Query(..., min_length=1, description="검색할 영화 제목 조각"),
):
    """
    KOBIS API를 직접 호출하여 실시간으로 영화 제목을 자동완성해 줍니다.
    """
    # I/O 블로킹 방지를 위해 asyncio.to_thread 사용 권장
    import asyncio
    results = await asyncio.to_thread(_kobis_client.search_movie_list, q)
    return {"query": q, "suggestions": results}
