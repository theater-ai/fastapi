
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.model import DailyBoxoffice, Movie, MovieCredit, Person, SCHEMA


class MovieRepository:
    """
    Movie / Person / MovieCredit / DailyBoxoffice DB 접근 전담.
    비즈니스 로직 없이 쿼리만 포함합니다.
    """

    # ── 조회 ─────────────────────────────────────────────────────────────────

    async def search(self, db: AsyncSession, query: str) -> list[Movie]:
        """제목(한글/영문) LIKE 검색. 최대 20건."""
        stmt = (
            select(Movie)
            .where(
                or_(
                    Movie.movie_nm.ilike(f"%{query}%"),
                    Movie.movie_nm_en.ilike(f"%{query}%"),
                )
            )
            .order_by(Movie.open_dt.desc().nullslast())
            .limit(20)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_credits(
        self, db: AsyncSession, movie_cd: str
    ) -> Movie | None:
        """영화 + 출연진 eager load."""
        stmt = (
            select(Movie)
            .options(selectinload(Movie.credits).selectinload(MovieCredit.person))
            .where(Movie.movie_cd == movie_cd)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_boxoffice(
        self,
        db: AsyncSession,
        movie_cd: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[DailyBoxoffice]:
        """박스오피스 시계열 조회 (기간 필터 선택)."""
        stmt = (
            select(DailyBoxoffice)
            .where(DailyBoxoffice.movie_cd == movie_cd)
            .order_by(DailyBoxoffice.target_date)
        )
        if date_from:
            stmt = stmt.where(DailyBoxoffice.target_date >= date_from)
        if date_to:
            stmt = stmt.where(DailyBoxoffice.target_date <= date_to)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ── 저장 ─────────────────────────────────────────────────────────────────

    async def upsert_movie(self, db: AsyncSession, movie_data: dict) -> Movie:
        """영화 마스터 upsert 후 ORM 객체 반환."""
        await db.execute(
            pg_insert(Movie)
            .values(**movie_data)
            .on_conflict_do_update(
                index_elements=["movie_cd"],
                set_={
                    "movie_nm": movie_data["movie_nm"],
                    "movie_nm_en": movie_data["movie_nm_en"],
                    "rep_nation_nm": movie_data["rep_nation_nm"],
                    "poster_url": movie_data["poster_url"],
                    "synopsis": movie_data["synopsis"],
                },
            )
        )
        await db.flush()
        result = await db.execute(
            select(Movie).where(Movie.movie_cd == movie_data["movie_cd"])
        )
        return result.scalar_one()

    async def upsert_person(self, db: AsyncSession, people_cd: str, people_nm: str) -> None:
        await db.execute(
            pg_insert(Person)
            .values(people_cd=people_cd, people_nm=people_nm)
            .on_conflict_do_nothing()
        )

    async def upsert_credit(
        self,
        db: AsyncSession,
        movie_cd: str,
        people_cd: str,
        role_type: str,
        cast_nm: Optional[str],
    ) -> None:
        await db.execute(
            pg_insert(MovieCredit)
            .values(
                movie_cd=movie_cd,
                people_cd=people_cd,
                role_type=role_type,
                cast_nm=cast_nm,
            )
            .on_conflict_do_nothing()
        )

    async def upsert_boxoffice_rows(
        self, db: AsyncSession, df: pd.DataFrame
    ) -> int:
        """DataFrame 행을 daily_boxoffice에 upsert. 적재 행 수 반환."""
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            await db.execute(
                pg_insert(DailyBoxoffice)
                .values(**row_dict)
                .on_conflict_do_update(
                    index_elements=["movie_cd", "target_date"],
                    set_={
                        "rank_num": row_dict.get("rank_num"),
                        "audi_cnt": row_dict.get("audi_cnt"),
                        "sales_amt": row_dict.get("sales_amt"),
                    },
                )
            )
        await db.flush()
        return len(df)