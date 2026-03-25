import operator
from typing import TypedDict, Annotated, List
from src.core.model import Movie

class ChatState(TypedDict):
    session_id: str                 # 대화 세션 식별자 (예: UUID)
    user_message: str               # 사용자가 보낸 메시지
    chat_history: List[str]         # 대화 히스토리 (사용자와 AI의 메시지 누적)
    mentioned_movies: List[str]     # 대화 중 언급된 영화 제목 리스트

    # 검색된 영화 정보 리스트 (히스토리에 누적)
    context_movies: Annotated[List[dict], operator.add]
    missing_movies: List[str]       # DB에 없는 영화 제목 리스트

    ai_response: str                # AI가 생성한 응답 메시지
