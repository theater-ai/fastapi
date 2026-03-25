from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from src.agent.state import ChatState
from src.core.config import get_settings

settings = get_settings()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=settings.OPENAI_API_KEY
)

async def answer_node(state: ChatState):
    context_movies = state.get("context_movies", [])
    chat_history = state.get("chat_history", [])
    
    context_text = ""
    if not context_movies:
        context_text = "제공할 수 있는 추가 영화 데이터가 없습니다."
    else:
        for m in context_movies:
            # 딕셔너리 접근 방식으로 변경
            context_text += f"- 영화명: {m['movie_nm']} ({m['movie_nm_en']})\n"
            context_text += f"  개봉일: {m['open_dt']}\n"
            context_text += f"  장르: {m['rep_genre_nm']}\n\n"

    system_prompt = f"""당신은 친절하고 전문적인 영화 데이터 분석 어시스턴트입니다.
이전 대화 맥락을 기억하고, 새롭게 제공된 [최신 검색된 영화 데이터]를 바탕으로 질문에 답변하세요.
데이터에 없는 내용이라면 지어내지 말고, "해당 정보는 아직 데이터에 없습니다"라고 솔직하게 답변하세요.

[최신 검색된 영화 데이터]
{context_text}
"""

    messages = [SystemMessage(content=system_prompt)]
    
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    if not chat_history or chat_history[-1]["content"] != state["user_message"]:
        messages.append(HumanMessage(content=state["user_message"]))

    response = await llm.ainvoke(messages)
    
    return {
        "ai_response": response.content
    }