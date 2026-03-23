from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.model import DailyBoxoffice, Movie, MovieCredit
from src.repository.movie import MovieRepository

_repo = MovieRepository()


@dataclass
class DashboardResult:
    movie: Movie
    directors: list[MovieCredit]
    actors: list[MovieCredit]
    boxoffice: list[DailyBoxoffice]
    total_audi: int
    total_sales: int
    peak_audi_date: Optional[date]
    peak_sales_date: Optional[date]


class MovieService:
    """
    영화 조회 및 대시보드 집계 전담.
    외부 API 호출이나 스크래핑은 포함하지 않습니다.
    """

    async def search(self, db: AsyncSession, query: str) -> list[Movie]:
        return await _repo.search(db, query)

    async def get_dashboard(
        self,
        db: AsyncSession,
        movie_cd: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> DashboardResult:
        movie = await _repo.get_with_credits(db, movie_cd)
        if not movie:
            raise ValueError(f"movie_cd='{movie_cd}' 에 해당하는 영화가 없습니다.")

        boxoffice = await _repo.get_boxoffice(db, movie_cd, date_from, date_to)

        directors = [c for c in movie.credits if c.role_type == "감독"]
        actors = [c for c in movie.credits if c.role_type == "배우"]

        # 누적 집계는 마지막 행 기준
        last = boxoffice[-1] if boxoffice else None
        total_audi = int(last.acc_audi_cnt or 0) if last else 0
        total_sales = int(last.acc_sales_amt or 0) if last else 0

        peak_audi = max(boxoffice, key=lambda r: r.audi_cnt or 0, default=None)
        peak_sales = max(boxoffice, key=lambda r: r.sales_amt or 0, default=None)

        return DashboardResult(
            movie=movie,
            directors=directors,
            actors=actors,
            boxoffice=boxoffice,
            total_audi=total_audi,
            total_sales=total_sales,
            peak_audi_date=peak_audi.target_date if peak_audi else None,
            peak_sales_date=peak_sales.target_date if peak_sales else None,
        )