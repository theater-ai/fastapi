from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    """POST /movies/scrape 바디 (title을 query param 대신 바디로도 받을 수 있도록 준비)"""
    title: str = Field(..., min_length=1, max_length=100, examples=["파묘"])


class DashboardQuery(BaseModel):
    """GET /movies/{movie_cd}/dashboard 쿼리 파라미터 모델"""
    date_from: Optional[date] = Field(None, description="조회 시작일 (YYYY-MM-DD)")
    date_to: Optional[date] = Field(None, description="조회 종료일 (YYYY-MM-DD)")