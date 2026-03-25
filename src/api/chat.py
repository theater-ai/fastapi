import re
from src.agent.graph import build_chat_graph
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.api.deps import get_current_user_email
from pydantic import BaseModel
from sqlalchemy import select
from src.core.model import ChatMessage
from src.api.deps import verify_internal
from src.service.chat import process_langgraph_chat

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
    # dependencies=[Depends(verify_internal)]  # 잠시
)

class ChatMessageRequest(BaseModel):
    message: str

@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    # user_email: str = Depends(get_current_user_email), 잠시
    db: AsyncSession = Depends(get_db)
):
    """세션의 과거 대화 내역 조회"""
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return {"session_id": session_id, "messages": messages}

@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    payload: ChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1. 사용자 메시지 저장
    user_msg = ChatMessage(session_id=session_id, role="user", content=payload.message)
    db.add(user_msg)
    await db.commit()

    # 2. LangGraph 에이전트 실행
    result = await process_langgraph_chat(session_id, payload.message, db)

    # 3. AI 응답 저장
    ai_msg = ChatMessage(session_id=session_id, role="assistant", content=result["content"])
    db.add(ai_msg)
    await db.commit()

    # 4. 결과 반환 (프론트엔드에 승인 필요 여부를 알려줌)
    return {
        "session_id": session_id,
        "role": "assistant",
        "content": result["content"],
        "is_approval_required": result["is_approval_required"],
        "missing_movies": result["missing_movies"]
    }
