
import requests

from src.core.config import get_settings

settings = get_settings()


class KobisClient:
    """
    KOBIS Open API 클라이언트.
    네트워크 I/O만 담당하며 비즈니스 로직은 포함하지 않습니다.
    """
    BASE_URL = "http://www.kobis.or.kr/kobisopenapi/webservice/rest"

    def __init__(self) -> None:
        self._api_key = settings.KOBIS_API_KEY

    def get_movie_code(self, title: str) -> str | None:
        """영화 제목으로 movie_cd 조회. 정확히 일치하는 첫 번째 항목 반환."""
        resp = requests.get(
            f"{self.BASE_URL}/movie/searchMovieList.json",
            params={"key": self._api_key, "movieNm": title},
            timeout=10,
        )
        resp.raise_for_status()

        movie_list = resp.json().get("movieListResult", {}).get("movieList", [])
        for movie in movie_list:
            if movie.get("movieNm") == title:
                return movie.get("movieCd")
        return None

    def get_movie_detail(self, movie_cd: str) -> dict:
        """movie_cd로 상세정보(감독·배우·장르 등) 조회."""
        resp = requests.get(
            f"{self.BASE_URL}/movie/searchMovieInfo.json",
            params={"key": self._api_key, "movieCd": movie_cd},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("movieInfoResult", {}).get("movieInfo", {})

    def search_movie_list(self, keyword: str, limit: int = 10) -> list[dict]:
        """자동완성을 위해 KOBIS에서 영화 목록을 실시간으로 검색."""
        resp = requests.get(
            f"{self.BASE_URL}/movie/searchMovieList.json",
            params={"key": self._api_key, "movieNm": keyword, "itemPerPage": limit},
            timeout=10,
        )
        resp.raise_for_status()
        
        movie_list = resp.json().get("movieListResult", {}).get("movieList", [])
        
        # 필요한 정보(제목, 영문제목, 개봉일, 감독 등)만 정제해서 반환
        results = []
        for m in movie_list:
            # 감독 이름 추출 (배열 형태로 올 수 있음)
            directors = [d.get("peopleNm") for d in m.get("directors", [])]
            director_str = directors[0] if directors else "감독미상"
            
            results.append({
                "movie_cd": m.get("movieCd"),
                "movie_nm": m.get("movieNm"),
                "open_dt": m.get("openDt"),
                "director": director_str
            })
        return results
