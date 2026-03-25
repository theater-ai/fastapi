from sqlalchemy.ext.asyncio import AsyncSession
from src.agent.state import ChatState
from src.service.scrape import ScrapeService

class ScraperNode:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scrape_service = ScrapeService()

    async def __call__(self, state: ChatState):
        missing = state.get("missing_movies", [])
        newly_found = []
        
        print(f"[{state['session_id']}] {len(missing)}건 수집 시작...")
        
        for title in missing:
            try:
                movie, _ = await self.scrape_service.scrape_and_save(self.db, title)
                # ORM 객체를 dict로 변환
                newly_found.append({
                    "movie_nm": movie.movie_nm,
                    "movie_nm_en": movie.movie_nm_en,
                    "open_dt": str(movie.open_dt) if movie.open_dt else None,
                    "rep_genre_nm": movie.rep_genre_nm,
                    "rep_nation_nm": movie.rep_nation_nm
                })
            except Exception as e:
                print(f"수집 실패 ({title}): {e}")
        
        return {
            "context_movies": newly_found,
            "missing_movies": []
        }