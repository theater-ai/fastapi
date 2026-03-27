from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PersonOut(_OrmBase):
    people_cd: str
    people_nm: str
    people_nm_en: Optional[str] = None


class CreditOut(_OrmBase):
    role_type: str
    cast_nm: Optional[str] = None
    person: PersonOut


class MovieSummaryOut(_OrmBase):
    movie_cd: str
    movie_nm: str
    movie_nm_en: Optional[str] = None
    open_dt: Optional[date] = None
    rep_genre_nm: Optional[str] = None
    rep_nation_nm: Optional[str] = None
    poster_url: Optional[str] = None
    synopsis: Optional[str] = None

class BoxofficeRowOut(_OrmBase):
    target_date: date
    rank_num: Optional[int] = None
    screen_cnt: Optional[int] = None
    screen_share: Optional[Decimal] = None
    show_cnt: Optional[int] = None
    show_share: Optional[Decimal] = None
    seat_cnt: Optional[int] = None
    seat_share: Optional[Decimal] = None
    seat_sales_rate: Optional[Decimal] = None
    sales_amt: Optional[int] = None
    sales_change_dod: Optional[int] = None
    audi_cnt: Optional[int] = None
    audi_change_dod: Optional[int] = None
    acc_sales_amt: Optional[int] = None
    acc_audi_cnt: Optional[int] = None


class DashboardOut(BaseModel):
    movie: MovieSummaryOut
    directors: List[CreditOut]
    actors: List[CreditOut]
    boxoffice: List[BoxofficeRowOut]
    total_audi: int
    total_sales: int
    peak_audi_date: Optional[date] = None
    peak_sales_date: Optional[date] = None


class ScrapeOut(BaseModel):
    movie_cd: str
    movie_nm: str
    boxoffice_rows: int
    message: str


class SearchOut(BaseModel):
    query: str
    count: int
    results: List[MovieSummaryOut]


class ErrorOut(BaseModel):
    detail: str