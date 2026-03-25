import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.agent.graph import build_chat_graph
from src.core.model import ChatMessage

async def process_langgraph_chat(session_id: str, user_message: str, db: AsyncSession) -> dict:
    app = build_chat_graph(db)
    config = {"configurable": {"thread_id": session_id}}

    # 1. DB에서 이전 대화 내역 가져오기 (방금 저장된 사용자 메시지 포함 최신 10건)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    # 오래된 순서대로 LLM에 넣어야 하므로 [::-1]로 역순 정렬
    history = result.scalars().all()[::-1]

    formatted_history = [{"role": msg.role, "content": msg.content} for msg in history]

    # '@' 뒤의 한글/영문/숫자만 추출
    mentioned = re.findall(r'@([가-힣a-zA-Z0-9]+)', user_message)
    
    initial_input = {
        "session_id": session_id,
        "user_message": user_message,
        "chat_history": formatted_history,  # 그래프 상태에 대화 내역 주입
        "mentioned_movies": mentioned,
        "context_movies": [],
        "missing_movies": []
    }
    
    async for event in app.astream(initial_input, config, stream_mode="values"):
        final_state = event

    return {
        "content": final_state.get("ai_response", "응답을 생성하지 못했습니다."),
        "is_approval_required": False,
        "missing_movies": final_state.get("missing_movies", [])
    }