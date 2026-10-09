"""
AI Assistant Orchestrator.

Luồng xử lý một câu hỏi:
  1. Xác thực phiên chat và quyền sở hữu
  2. Đọc lịch sử, lưu câu hỏi
  3. Phân loại ý định (intent_classifier)
  4. Chạy năng lực phù hợp: RAG tri thức / thời tiết trực tiếp / cả hai / xã giao
  5. Sinh câu trả lời bằng LLM có ràng buộc ngữ cảnh (hoặc từ chối nếu không có tri thức phù hợp)
  6. Lưu câu trả lời và nguồn trích dẫn
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.schemas.chat import ChatQueryResponse, ChatSourceItem
from backend.services.chat_service import (
    create_chat_message,
    get_chat_messages,
    resolve_and_authorize_session,
)
from backend.services.intent_classifier import (  # noqa: F401  (re-export cho các module/test cũ)
    TASK_GENERAL,
    TASK_HYBRID,
    TASK_KNOWLEDGE,
    TASK_WEATHER,
    build_retrieval_query,
    classify_assistant_intent,
    extract_region_from_text,
)
from backend.services.weather_service import fetch_and_sync_live_weather
from database.models import ChatSession, User
from rag.retriever import RAGRetriever
from rag.vector_store import IndexNotReadyError

logger = logging.getLogger("tea_scholar.assistant_service")

DEFAULT_SESSION_TITLE = "Cuộc trò chuyện mới"
SESSION_TITLE_MAX_CHARS = 40
RETRIEVAL_TOP_K = 3

NO_KNOWLEDGE_ANSWER = (
    "Hiện tại cơ sở tri thức chưa tìm thấy nguồn thông tin đủ phù hợp để giải đáp chính xác câu hỏi này. "
    "Bạn có thể diễn đạt lại, hoặc hỏi về kỹ thuật trồng, chăm sóc, bón phân, đốn hái, sâu bệnh hại "
    "và chế biến chè."
)
GREETING_ANSWER = (
    "Xin chào! Tôi là Tea Scholar AI, trợ lý tri thức về cây chè Việt Nam. Tôi có thể giải đáp về kỹ thuật "
    "trồng và chăm sóc, sâu bệnh hại, thu hoạch – chế biến chè và thời tiết các vùng chè. Bạn muốn hỏi gì?"
)
# Câu LLM dùng khi từ chối (xem SYSTEM_PROMPT). Câu từ chối ngắn không cần kèm nguồn trích dẫn.
LLM_REFUSAL_MARKER = "chưa có đủ thông tin"
LLM_REFUSAL_MAX_CHARS = 200

THANKS_ANSWER = "Rất vui được hỗ trợ bạn. Nếu cần thêm thông tin về cây chè, bạn cứ hỏi nhé!"
GOODBYE_ANSWER = "Tạm biệt bạn! Chúc bạn một mùa chè bội thu."

_default_retriever: Optional[RAGRetriever] = None


def get_default_retriever() -> RAGRetriever:
    """
    RAGRetriever dùng chung cho toàn tiến trình.
    Khởi tạo nạp model embedding và chỉ mục vector nên chỉ thực hiện một lần.
    """
    global _default_retriever
    if _default_retriever is None:
        retriever = RAGRetriever()
        retriever.load()
        _default_retriever = retriever
    return _default_retriever


@dataclass
class Evidence:
    """Bằng chứng thu thập được cho một câu hỏi."""
    rag_context: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    weather_context: Optional[str] = None
    knowledge_found: bool = False


def _small_talk_answer(message: str) -> str:
    lowered = message.lower()
    if "cảm ơn" in lowered:
        return THANKS_ANSWER
    if "tạm biệt" in lowered:
        return GOODBYE_ANSWER
    return GREETING_ANSWER


def _retrieve_knowledge(query: str, retriever: Optional[RAGRetriever]) -> Evidence:
    try:
        result = (retriever or get_default_retriever()).retrieve(query=query, top_k=RETRIEVAL_TOP_K)
    except IndexNotReadyError as err:
        logger.error("[Assistant] RAG index unavailable: %s", err)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))

    if not result.get("is_relevant"):
        # Các chunk dưới ngưỡng không liên quan tới câu hỏi nên không đưa vào ngữ cảnh hay danh sách nguồn.
        return Evidence(knowledge_found=False)

    sources = [
        {
            "chunk_id": chunk.get("chunk_id", ""),
            "title": chunk.get("metadata", {}).get("title", ""),
            "source": chunk.get("metadata", {}).get("source", ""),
            "similarity_score": chunk.get("similarity_score", 0.0),
        }
        for chunk in result.get("retrieved_chunks", [])
    ]
    return Evidence(rag_context=result.get("context_text", ""), sources=sources, knowledge_found=True)


async def _fetch_weather_context(db: Session, region: str, strict: bool) -> str:
    """strict=True: lỗi thời tiết được ném ra (câu hỏi thuần thời tiết); ngược lại chỉ ghi chú lỗi vào ngữ cảnh."""
    try:
        w = await fetch_and_sync_live_weather(db=db, region=region)
    except HTTPException as err:
        logger.warning("[Assistant] Weather capability error: %s", err.detail)
        if strict:
            raise
        return f"Không thể lấy dữ liệu thời tiết trực tiếp cho vùng '{region}': {err.detail}"

    recorded = w.recorded_at.strftime("%Y-%m-%d %H:%M:%S UTC") if w.recorded_at else "Hiện tại"
    return (
        f"Tỉnh/Vùng: {w.region}\n"
        f"Nhiệt độ: {w.temperature}°C\n"
        f"Độ ẩm: {w.humidity}%\n"
        f"Lượng mưa: {w.rainfall} mm\n"
        f"Tốc độ gió: {w.wind_speed} m/s\n"
        f"Trạng thái thời tiết: {w.weather_condition}\n"
        f"Thời điểm ghi nhận dữ liệu: {recorded}"
    )


def _reply(db: Session, session: ChatSession, answer: str, sources: List[Dict[str, Any]]) -> ChatQueryResponse:
    sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
    msg = create_chat_message(db, session_id=session.id, role="assistant", content=answer, sources_json=sources_json)
    return ChatQueryResponse(
        session_id=session.id,
        message_id=msg.id,
        role="assistant",
        answer=answer,
        sources=[ChatSourceItem(**s) for s in sources],
        created_at=msg.created_at,
    )


async def orchestrate_assistant_response(
    db: Session,
    session_id: Optional[int],
    message: str,
    current_user: Optional[User],
    retriever: Optional[RAGRetriever] = None,
) -> ChatQueryResponse:
    clean_msg = message.strip()
    if not clean_msg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty")

    session = resolve_and_authorize_session(db, session_id=session_id, current_user=current_user)

    history_turns = [
        {"role": m.role, "content": m.content}
        for m in get_chat_messages(db, session.id)
        if m.role in ("user", "assistant")
    ]
    previous_user_messages = [t["content"] for t in history_turns if t["role"] == "user"]

    create_chat_message(db, session_id=session.id, role="user", content=clean_msg)
    if session.title == DEFAULT_SESSION_TITLE:
        session.title = clean_msg[:SESSION_TITLE_MAX_CHARS]
        db.commit()

    intent = classify_assistant_intent(
        query=clean_msg,
        history_text=" ".join(t["content"] for t in history_turns[-4:]),
    )
    task_type = intent["task_type"]
    logger.info("[Assistant] '%s' -> %s (region=%s)", clean_msg, task_type, intent["detected_region"])

    if task_type == TASK_GENERAL:
        return _reply(db, session, _small_talk_answer(clean_msg), [])

    evidence = Evidence()
    if task_type in (TASK_KNOWLEDGE, TASK_HYBRID):
        retrieval_query = build_retrieval_query(clean_msg, previous_user_messages)
        evidence = _retrieve_knowledge(retrieval_query, retriever)
        if task_type == TASK_KNOWLEDGE and not evidence.knowledge_found:
            return _reply(db, session, NO_KNOWLEDGE_ANSWER, [])

    if task_type in (TASK_WEATHER, TASK_HYBRID):
        evidence.weather_context = await _fetch_weather_context(
            db, intent["detected_region"], strict=(task_type == TASK_WEATHER)
        )

    # Gọi qua module chat_service để test có thể mock generate_rag_response
    import backend.services.chat_service as chat_svc
    answer = await chat_svc.generate_rag_response(
        query=clean_msg,
        context_text=evidence.rag_context,
        history_turns=history_turns,
        weather_context=evidence.weather_context,
    )
    sources = evidence.sources
    if len(answer) <= LLM_REFUSAL_MAX_CHARS and LLM_REFUSAL_MARKER in answer.lower():
        # LLM đã tự từ chối vì ngữ cảnh không liên quan: không hiển thị các chunk lạc đề như nguồn tham khảo
        sources = []
    return _reply(db, session, answer, sources)
