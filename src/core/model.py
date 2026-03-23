"""
core/model.py

SQLAlchemy ORM 모델 정의.
모든 테이블은 'movie' 스키마에 생성됩니다.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

SCHEMA = "movie"


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movie"
    __table_args__ = {"schema": SCHEMA}

    movie_cd: Mapped[str] = mapped_column(String(20), primary_key=True)
    movie_nm: Mapped[str] = mapped_column(String(255), nullable=False)
    movie_nm_en: Mapped[Optional[str]] = mapped_column(String(255))
    open_dt: Mapped[Optional[date]] = mapped_column(Date)
    rep_genre_nm: Mapped[Optional[str]] = mapped_column(String(50))
    rep_nation_nm: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    credits: Mapped[List["MovieCredit"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    boxoffice_records: Mapped[List["DailyBoxoffice"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Movie cd={self.movie_cd!r} nm={self.movie_nm!r}>"


class Person(Base):
    __tablename__ = "person"
    __table_args__ = {"schema": SCHEMA}  # 버그 수정: __tagle_args__ → __table_args__

    people_cd: Mapped[str] = mapped_column(String(20), primary_key=True)
    people_nm: Mapped[str] = mapped_column(String(100), nullable=False)
    people_nm_en: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    credits: Mapped[List["MovieCredit"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Person cd={self.people_cd!r} nm={self.people_nm!r}>"


class MovieCredit(Base):
    __tablename__ = "movie_credit"
    __table_args__ = (
        UniqueConstraint("movie_cd", "people_cd", "role_type", name="uq_movie_credit"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    movie_cd: Mapped[str] = mapped_column(
        String(20), ForeignKey(f"{SCHEMA}.movie.movie_cd", ondelete="CASCADE")
    )
    people_cd: Mapped[str] = mapped_column(
        String(20), ForeignKey(f"{SCHEMA}.person.people_cd", ondelete="CASCADE")
    )
    role_type: Mapped[str] = mapped_column(String(20))   # '감독' | '배우'
    cast_nm: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    movie: Mapped["Movie"] = relationship(back_populates="credits")
    person: Mapped["Person"] = relationship(back_populates="credits")

    def __repr__(self) -> str:
        return f"<MovieCredit movie={self.movie_cd!r} person={self.people_cd!r} role={self.role_type!r}>"


class DailyBoxoffice(Base):
    __tablename__ = "daily_boxoffice"
    __table_args__ = (
        UniqueConstraint("movie_cd", "target_date", name="uq_daily_boxoffice"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    movie_cd: Mapped[str] = mapped_column(
        String(20), ForeignKey(f"{SCHEMA}.movie.movie_cd", ondelete="CASCADE")
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    rank_num: Mapped[Optional[int]] = mapped_column(Integer)
    screen_cnt: Mapped[Optional[int]] = mapped_column(Integer)
    screen_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    show_cnt: Mapped[Optional[int]] = mapped_column(Integer)
    show_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    seat_cnt: Mapped[Optional[int]] = mapped_column(Integer)
    seat_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    seat_sales_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    sales_amt: Mapped[Optional[int]] = mapped_column(BigInteger)
    sales_change_dod: Mapped[Optional[int]] = mapped_column(BigInteger)
    audi_cnt: Mapped[Optional[int]] = mapped_column(Integer)
    audi_change_dod: Mapped[Optional[int]] = mapped_column(Integer)
    acc_sales_amt: Mapped[Optional[int]] = mapped_column(BigInteger)
    acc_audi_cnt: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    movie: Mapped["Movie"] = relationship(back_populates="boxoffice_records")

    def __repr__(self) -> str:
        return f"<DailyBoxoffice movie={self.movie_cd!r} date={self.target_date!r}>"