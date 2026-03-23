"""
KOBIS 박스오피스 HTML 다운로드 및 DataFrame 파싱.
"""

import io

import pandas as pd
import requests
from bs4 import BeautifulSoup

_KOBIS_BASE = "https://www.kobis.or.kr/kobis/business"
_CSRF_URL = f"{_KOBIS_BASE}/mast/mvie/searchMovieList.do"
_DOWNLOAD_URL = f"{_KOBIS_BASE}/mast/mvie/searchMovieDtlXls.do"

# KOBIS 컬럼명 → 내부 필드명 매핑
COLUMN_MAP: dict[str, str] = {
    "날짜": "target_date",
    "순위": "rank_num",
    "스크린수": "screen_cnt",
    "스크린점유율": "screen_share",
    "상영횟수": "show_cnt",
    "상영점유율": "show_share",
    "좌석수": "seat_cnt",
    "좌석점유율": "seat_share",
    "좌석판매율": "seat_sales_rate",
    "매출액": "sales_amt",
    "매출액증감(전일대비)": "sales_change_dod",
    "관객수": "audi_cnt",
    "관객수증감(전일대비)": "audi_change_dod",
    "누적매출액": "acc_sales_amt",
    "누적관객수": "acc_audi_cnt",
}

_SKIP_PATTERNS = ("합계", "평균", "조회일", "날짜")


def _clean_numeric(val: object) -> int | float:
    """'5,173 ( 100.0% )' 형태 문자열에서 숫자만 추출."""
    if pd.isna(val):
        return 0
    s = str(val).replace(",", "").replace("%", "").split("(")[0].strip()
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return 0


def fetch_boxoffice(movie_cd: str) -> pd.DataFrame | None:
    """
    movie_cd에 해당하는 박스오피스 데이터를 스크래핑하여 정제된 DataFrame 반환.
    실패 시 None 반환.
    """
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # CSRF 토큰 획득
        csrf_resp = session.get(_CSRF_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(csrf_resp.text, "html.parser")
        csrf_input = soup.select_one('input[name="CSRFToken"]')
        if not csrf_input:
            raise ValueError("CSRF 토큰을 찾을 수 없습니다.")
        csrf_token = csrf_input["value"]

        # 박스오피스 HTML 다운로드
        dl_resp = session.post(
            _DOWNLOAD_URL,
            data={"code": movie_cd, "sType": "box", "CSRFToken": csrf_token},
            headers=headers,
            timeout=30,
        )
        dl_resp.encoding = "utf-8"

        # '날짜' 컬럼이 있는 테이블 탐색
        tables = pd.read_html(io.StringIO(dl_resp.text))
        target_df = next(
            (
                df
                for df in tables
                if "날짜" in "".join(df.columns.astype(str))
                or (not df.empty and "날짜" in "".join(df.iloc[0].astype(str)))
            ),
            None,
        )
        if target_df is None:
            return None

        # 첫 행이 헤더인 경우 처리
        if "날짜" not in target_df.columns:
            target_df.columns = target_df.iloc[0]
            target_df = target_df.iloc[1:].reset_index(drop=True)

        # 컬럼명 정제 및 불필요 행 제거
        target_df.columns = [str(c).strip() for c in target_df.columns]
        target_df = target_df.dropna(subset=["날짜"])
        target_df = target_df[
            ~target_df["날짜"].astype(str).str.contains("|".join(_SKIP_PATTERNS))
        ]

        # 존재하는 컬럼만 매핑
        available = {k: v for k, v in COLUMN_MAP.items() if k in target_df.columns}
        target_df = target_df[list(available)].rename(columns=available)

        # 날짜 파싱 및 숫자 정제
        target_df["target_date"] = pd.to_datetime(target_df["target_date"]).dt.date
        for col in target_df.columns:
            if col != "target_date":
                target_df[col] = target_df[col].apply(_clean_numeric)

        return target_df

    except Exception as exc:
        print(f"[Scraper] Error for movie_cd={movie_cd}: {exc}")
        return None