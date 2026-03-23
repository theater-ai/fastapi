
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
