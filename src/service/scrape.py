import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.model import Movie
from src.external.kobis import KobisClient
from src.external.scraper import fetch_boxoffice
from src.repository.movie import MovieRepository

_kobis = KobisClient()
_repo = MovieRepository()


def _parse_open_dt(raw: str) -> date | None:
    """'YYYYMMDD' 문자열 → date 객체. 형식이 맞지 않으면 None."""
    if raw and len(raw) == 8:
        try:
            return date(int(raw[:4]), int(raw[4:6]), int(raw[6:]))
        except ValueError:
            pass
    return None


class ScrapeService:
    """
    KOBIS API 호출 + 스크래핑 + DB 저장 파이프라인 전담.
    blocking I/O(requests)는 스레드 풀에서 실행합니다.
    """

    async def scrape_and_save(
        self, db: AsyncSession, title: str
    ) -> tuple[Movie, int]:
        """
        1) KOBIS API로 movie_cd 조회
        2) 영화 상세정보 + 출연진 저장
        3) 박스오피스 스크래핑 → DB upsert
        반환: (Movie 객체, 적재된 박스오피스 행 수)
        """
        loop = asyncio.get_event_loop()

        # blocking I/O → 스레드 풀 실행
        movie_cd = await loop.run_in_executor(None, _kobis.get_movie_code, title)
        if not movie_cd:
            raise ValueError(f"KOBIS에서 '{title}' 영화 코드를 찾을 수 없습니다.")

        info = await loop.run_in_executor(None, _kobis.get_movie_detail, movie_cd)

        movie = await self._save_movie_and_credits(db, info)

        df = await loop.run_in_executor(None, fetch_boxoffice, movie_cd)
        bo_count = 0
        if df is not None:
            df["movie_cd"] = movie_cd
            bo_count = await _repo.upsert_boxoffice_rows(db, df)

        return movie, bo_count

    async def _save_movie_and_credits(
        self, db: AsyncSession, info: dict
    ) -> Movie:
        movie_data = {
            "movie_cd": info["movieCd"],
            "movie_nm": info["movieNm"],
            "movie_nm_en": info.get("movieNmEn"),
            "open_dt": _parse_open_dt(info.get("openDt", "")),
            "rep_genre_nm": (
                info["genres"][0]["genreNm"] if info.get("genres") else None
            ),
        }
        movie = await _repo.upsert_movie(db, movie_data)

        credits = [
            (d["peopleNm"], "감독", None)
            for d in info.get("directors", [])
        ] + [
            (a["peopleNm"], "배우", a.get("cast"))
            for a in info.get("actors", [])
        ]

        for name, role, cast in credits:
            p_cd = f"P_{name}"
            await _repo.upsert_person(db, p_cd, name)
            await _repo.upsert_credit(db, movie.movie_cd, p_cd, role, cast)

        return movie