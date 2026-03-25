from sqlalchemy.ext.asyncio import AsyncSession
from src.agent.state import ChatState
from src.repository.movie import MovieRepository

class RetrieverNode:
    def __init__(self, repo: MovieRepository, db: AsyncSession):
        self.repo = repo
        self.db = db

    async def __call__(self, state: ChatState):
        print(f"[{state['session_id']}] DB 검색 중...")
        mentioned_movies = state.get("mentioned_movies", [])
        
        found_movies = []
        missing_movies = []

        for title in mentioned_movies:
            results = await self.repo.search(self.db, title)
            if results:
                m = results[0]
                # ORM 객체를 dict로 변환
                found_movies.append({
                    "movie_nm": m.movie_nm,
                    "movie_nm_en": m.movie_nm_en,
                    "open_dt": str(m.open_dt) if m.open_dt else None,
                    "rep_genre_nm": m.rep_genre_nm,
                    "rep_nation_nm": m.rep_nation_nm
                })
            else:
                missing_movies.append(title)
        
        return {
            "context_movies": found_movies,
            "missing_movies": missing_movies
        }