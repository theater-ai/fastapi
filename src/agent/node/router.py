from typing import Literal
from src.agent.state import ChatState

def route_after_search(state: ChatState) -> Literal["scrape", "generate"]:
    # DB에 없는 영화가 하나라도 있다면 바로 스크래핑 단계로
    if state.get("missing_movies"):
        return "scrape"
    return "generate"