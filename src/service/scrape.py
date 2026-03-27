import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.model import Movie
from src.external.kobis import KobisClient
from src.external.tmdb import TmdbClient
from src.external.scraper import fetch_boxoffice
from src.repository.movie import MovieRepository

_kobis = KobisClient()
_repo = MovieRepository()
_tmdb = TmdbClient()


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
        loop = asyncio.get_event_loop()
        
        # 1. KOBIS 개봉일 기반으로 연도 추출
        open_dt_str = info.get("openDt", "")
        release_year = open_dt_str[:4] if len(open_dt_str) >= 4 else None

        # 2. TMDB 상세 정보 조회 (스레드 풀 사용)
        tmdb_info = await loop.run_in_executor(
            None, _tmdb.get_movie_extra_info, info["movieNm"], release_year
        )

        # 3. KOBIS 데이터에 없는 국가 정보 보완
        # KOBIS는 nations 배열에 넣어주기도 하지만 repNationNm 컬럼을 쓰기도 함
        nation = info.get("repNationNm") or (info.get("nations")[0]["nationNm"] if info.get("nations") else None)
        
        # KOBIS에 국가가 없는데 TMDB엔 있다면 TMDB 국가 이름 사용
        if not nation and tmdb_info.get("production_countries"):
            nation = tmdb_info["production_countries"][0].get("name") # ex: "United States of America"

        # 4. 포스터 URL 및 시놉시스 추출
        poster_path = tmdb_info.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        synopsis = tmdb_info.get("overview")

        # 5. DB 적재용 데이터 구성
        movie_data = {
            "movie_cd": info["movieCd"],
            "movie_nm": info["movieNm"],
            "movie_nm_en": info.get("movieNmEn") or tmdb_info.get("original_title"), # 영문명도 TMDB로 보완 가능
            "open_dt": _parse_open_dt(open_dt_str),
            "rep_genre_nm": (info["genres"][0]["genreNm"] if info.get("genres") else None),
            "rep_nation_nm": nation,
            "poster_url": poster_url,
            "synopsis": synopsis,
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