from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.state import ChatState
from src.agent.node.retriever import RetrieverNode
from src.agent.node.scraper import ScraperNode
from src.agent.node.generator import answer_node
from src.agent.node.router import route_after_search
from src.repository.movie import MovieRepository

def build_chat_graph(db: AsyncSession):
    workflow = StateGraph(ChatState)
    
    # 1. 노드 등록 (ask_user 제거)
    repo = MovieRepository()
    workflow.add_node("retrieve", RetrieverNode(repo, db))
    workflow.add_node("scrape", ScraperNode(db))
    workflow.add_node("generate", answer_node)

    # 2. 에지 연결
    workflow.set_entry_point("retrieve")
    
    # 조건부 분기 (ask_user 대신 scrape로 직행)
    workflow.add_conditional_edges(
        "retrieve",
        route_after_search,
        {
            "scrape": "scrape",
            "generate": "generate"
        }
    )

    # 스크래핑 후 답변 생성으로 이동
    workflow.add_edge("scrape", "generate")
    workflow.add_edge("generate", END)

    # 3. 중단점(interrupt_before) 제거 - 논스톱 실행
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app