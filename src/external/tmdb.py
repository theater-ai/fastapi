import requests
from src.core.config import get_settings

settings = get_settings()

class TmdbClient:
    """
    TMDB API 클라이언트.
    영화 시놉시스, 포스터 이미지, 국가 정보 등을 보완하기 위해 사용합니다.
    """
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self) -> None:
        self._api_key = settings.TMDB_API_KEY

    def get_movie_extra_info(self, title: str, release_year: str | None = None) -> dict:
        """
        영화 제목과 개봉 연도(옵션)로 TMDB를 검색하여 상세 정보를 반환합니다.
        """
        if not self._api_key:
            return {}

        # 1. 영화 검색 (search/movie)
        search_params = {
            "api_key": self._api_key,
            "query": title,
            "language": "ko-KR",
        }
        if release_year:
            search_params["primary_release_year"] = release_year

        try:
            resp = requests.get(f"{self.BASE_URL}/search/movie", params=search_params, timeout=10)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            
            if not results:
                return {}

            # 가장 관련성 높은 첫 번째 결과 선택
            tmdb_id = results[0].get("id")

            # 2. 상세 정보 조회 (movie/{movie_id}) - 제작 국가 등을 정확히 얻기 위함
            detail_resp = requests.get(
                f"{self.BASE_URL}/movie/{tmdb_id}",
                params={"api_key": self._api_key, "language": "ko-KR"},
                timeout=10
            )
            detail_resp.raise_for_status()
            return detail_resp.json()

        except Exception as e:
            print(f"[TMDB] Fetch error for '{title}': {e}")
            return {}