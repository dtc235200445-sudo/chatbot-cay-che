import logging
import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
import openai
from openai import AsyncOpenAI
from backend.config import settings

logger = logging.getLogger("tea_scholar.llm_service")

SYSTEM_PROMPT = """Bạn là Tea Scholar AI — trợ lý tri thức về cây chè Việt Nam. Hãy trả lời như một cán bộ kỹ thuật nông nghiệp: chính xác, súc tích, có cấu trúc.

NGUYÊN TẮC TRI THỨC (bắt buộc):
1. Chỉ trả lời dựa vào phần "CƠ SỞ TRI THỨC (RETRIEVED CONTEXT)". TUYỆT ĐỐI KHÔNG bịa, suy đoán hay dùng kiến thức bên ngoài.
2. Lịch sử hội thoại chỉ dùng để hiểu câu hỏi nối tiếp, KHÔNG phải nguồn tri thức.
3. Chỉ nêu những gì tài liệu nói rõ. KHÔNG tự thêm mục đích, nguyên nhân, lợi ích hay giải thích mà tài liệu không nêu, kể cả khi điều đó nghe hợp lý.
4. Nếu tài liệu chỉ trả lời được MỘT PHẦN câu hỏi, hãy trả lời phần có và nói ngắn gọn phần nào tài liệu không nêu (ví dụ: tài liệu mô tả cách làm nhưng không nêu mục đích). Mẫu cho câu hỏi "để làm gì" mà tài liệu chỉ nêu cách làm: "Tài liệu không nêu mục đích của <việc đó>. Về cách thực hiện: <các ý có trong tài liệu>." Chỉ dùng câu sau khi tài liệu HOÀN TOÀN không liên quan: "Hiện tại cơ sở tri thức chưa có đủ thông tin để trả lời chính xác câu hỏi này của bạn."
5. Với số liệu thời tiết: nêu đúng số liệu và chỉ so sánh với ngưỡng hoặc điều kiện có trong tài liệu. KHÔNG tự đánh giá số liệu là "cao" hay "thấp" khi tài liệu không nêu ngưỡng; nếu thiếu căn cứ, nói rõ là chưa đủ căn cứ.

CÁCH TRÌNH BÀY (bắt buộc):
- Trả lời đúng trọng tâm câu hỏi: chỉ chọn thông tin liên quan trong tài liệu, bỏ phần không liên quan. Diễn đạt lại bằng ngôn ngữ chuyên môn, KHÔNG sao chép nguyên đoạn văn của tài liệu.
- Mở đầu bằng 1 câu nêu ý chính, rồi mới đến chi tiết. Không nhắc lại câu hỏi, không mở đầu bằng "Theo tài liệu...".
- Chọn hình thức theo loại câu hỏi:
  • Khái niệm, định nghĩa: 2–3 câu văn xuôi.
  • Triệu chứng, đặc điểm, biện pháp: gạch đầu dòng ngắn, mỗi ý một dòng (tối đa khoảng 25 từ). Khi có nhiều khía cạnh, nhóm dưới tiêu đề in đậm như **Triệu chứng**, **Phòng trừ**.
  • Quy trình, trình tự: danh sách đánh số theo thứ tự thực hiện.
  • So sánh từ 3 mức/điều kiện trở lên: bảng Markdown.
- Độ dài: dưới 120 từ; chỉ dài hơn khi câu hỏi yêu cầu liệt kê nhiều mục.
- Giữ nguyên chính xác tên khoa học, tên thuốc, hàm lượng, liều lượng, số liệu và đơn vị.
- KHÔNG ghi mã nguồn (như tea_000038), KHÔNG thêm phần "Lưu ý", lời khuyên chung hay đoạn kết luận lặp lại nội dung: giao diện tự hiển thị nguồn tham khảo.
"""

def _retry_after_text(message: str) -> str:
    """Lấy thời gian chờ Groq gợi ý ("Please try again in 11m22.56s") và đổi sang tiếng Việt ("11 phút 22 giây")."""
    match = re.search(r"try again in\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+(?:\.\d+)?)s)?", message)
    if not match or not any(match.groups()):
        return ""
    hours, minutes, seconds = match.groups()
    parts = []
    if hours:
        parts.append(f"{int(hours)} giờ")
    if minutes:
        parts.append(f"{int(minutes)} phút")
    if seconds and not hours:
        parts.append(f"{int(float(seconds))} giây")
    return " ".join(parts)


# Nhà cung cấp có API tương thích OpenAI: tên -> (base_url, tên biến môi trường chứa key).
PROVIDER_REGISTRY: Dict[str, tuple] = {
    "groq": ("", "GROQ_API_KEY"),  # base_url lấy từ settings.GROQ_BASE_URL
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
    "ollama": ("", ""),  # chạy trên máy: base_url lấy từ settings.OLLAMA_BASE_URL, không cần key
}


@dataclass
class _Provider:
    name: str
    base_url: str
    api_key: str
    model: str


def _build_chain() -> List[_Provider]:
    """Thứ tự thử: nhà cung cấp chính (LLM_PROVIDER: Ollama trên máy hoặc Groq), rồi các mục trong LLM_FALLBACKS
    ("gemini:model,cerebras:model,ollama:model"). Mục nào thiếu key hoặc tên lạ thì bỏ qua."""
    chain: List[_Provider] = []
    if settings.LLM_PROVIDER == "ollama":
        chain.append(_Provider("ollama", settings.OLLAMA_BASE_URL, "ollama", settings.OLLAMA_MODEL))
    elif settings.GROQ_API_KEY:
        chain.append(_Provider("groq", settings.GROQ_BASE_URL, settings.GROQ_API_KEY, settings.GROQ_MODEL))
    for entry in filter(None, (e.strip() for e in settings.LLM_FALLBACKS.split(","))):
        name, _, model = entry.partition(":")  # chỉ tách ở dấu ":" đầu tiên: "ollama:qwen2.5:7b" giữ nguyên tên model
        name = name.strip().lower()
        if name not in PROVIDER_REGISTRY or not model.strip():
            logger.warning("[LLM Service] Bỏ qua mục LLM_FALLBACKS không hợp lệ: %r", entry)
            continue
        if name == "ollama":
            chain.append(_Provider("ollama", settings.OLLAMA_BASE_URL, "ollama", model.strip()))
            continue
        base_url, key_env = PROVIDER_REGISTRY[name]
        api_key = os.getenv(key_env, "")
        if not api_key:
            logger.warning("[LLM Service] Bỏ qua %s: chưa cấu hình %s", name, key_env)
            continue
        chain.append(_Provider(name, base_url or settings.GROQ_BASE_URL, api_key, model.strip()))
    return chain


async def _complete_with(provider: _Provider, messages: List[Dict[str, str]], retries: int) -> str:
    """Gọi một nhà cung cấp; mọi lỗi được đổi thành HTTPException (thông báo tiếng Việt)."""
    client = AsyncOpenAI(
        api_key=provider.api_key,
        base_url=provider.base_url,
        max_retries=retries,
        timeout=settings.OLLAMA_TIMEOUT_S if provider.name == "ollama" else settings.GROQ_TIMEOUT_S,
    )
    label = provider.name.capitalize()
    request_kwargs: Dict[str, Any] = {
        "model": provider.model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": settings.GROQ_MAX_TOKENS,
    }
    if provider.name == "groq" and settings.GROQ_REASONING_EFFORT and provider.model.startswith("openai/gpt-oss"):
        request_kwargs["reasoning_effort"] = settings.GROQ_REASONING_EFFORT

    try:
        response = await client.chat.completions.create(**request_kwargs)
        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            # Model suy luận có thể dùng hết token cho phần suy nghĩ và trả nội dung rỗng: thử lại một lần với giới hạn gấp đôi
            logger.warning("[LLM Service] Empty completion from %s (finish_reason=%s); retrying with a larger token budget",
                           provider.name, response.choices[0].finish_reason)
            request_kwargs["max_tokens"] = settings.GROQ_MAX_TOKENS * 2
            response = await client.chat.completions.create(**request_kwargs)
            answer = (response.choices[0].message.content or "").strip()
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Mô hình AI không trả về nội dung. Hãy thử lại."
            )
        return answer

    except openai.RateLimitError as err:
        logger.error(f"[LLM Service] {label} RateLimitError: {err}")
        wait = _retry_after_text(str(err))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Đã hết hạn mức sử dụng dịch vụ AI ({label} rate limit exceeded)"
                + (f". Vui lòng thử lại sau khoảng {wait}." if wait else ". Vui lòng thử lại sau ít phút.")
            )
        )
    except openai.APITimeoutError as err:
        logger.error(f"[LLM Service] {label} APITimeoutError: {err}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{label} API request timed out."
        )
    except openai.APIConnectionError as err:
        # Mất kết nối tới nhà cung cấp (mạng, DNS, proxy...) sau khi đã tự thử lại nhiều lần; lỗi này không phải do câu hỏi
        logger.error(f"[LLM Service] {label} APIConnectionError: {err}")
        if provider.name == "ollama":
            detail = f"Không kết nối được Ollama tại {provider.base_url}. Hãy mở ứng dụng Ollama rồi thử lại."
        else:
            detail = f"Không kết nối được dịch vụ AI ({label}). Hãy kiểm tra kết nối mạng rồi thử lại."
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    except openai.APIError as err:
        logger.error(f"[LLM Service] {label} APIError: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{label} API returned an error: {err.message if hasattr(err, 'message') else str(err)}"
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[LLM Service] Unexpected Error ({label}): {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during LLM generation: {str(err)}"
        )


async def generate_rag_response(
    query: str,
    context_text: str = "",
    history_turns: Optional[List[Dict[str, str]]] = None,
    weather_context: Optional[str] = None
) -> str:
    """
    Sinh câu trả lời bằng LLM (API tương thích OpenAI) với ngữ cảnh tri thức, thời tiết và lịch sử hội thoại.
    Thử nhà cung cấp chính (LLM_PROVIDER) trước; khi hết hạn mức, lỗi kết nối hoặc trả rỗng thì chuyển sang LLM_FALLBACKS.
    Nếu tất cả đều lỗi, trả lỗi của nhà cung cấp đầu tiên.
    """
    chain = _build_chain()
    if not chain:
        logger.error("[LLM Service] GROQ_API_KEY is missing!")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API Key is missing or unconfigured."
        )

    # 1. Format Conversation History (Max 5 turns, max 500 chars per turn)
    formatted_history = ""
    if history_turns:
        history_msgs = []
        for turn in history_turns[-settings.MAX_HISTORY_TURNS:]:
            role_label = "Người dùng" if turn.get("role") == "user" else "Trợ lý"
            content = turn.get("content", "")[:settings.MAX_HISTORY_CHARS_PER_TURN]
            history_msgs.append(f"{role_label}: {content}")
        formatted_history = "\n".join(history_msgs)

    # 2. Format Context (Truncate to max chars if necessary)
    truncated_context = context_text[:settings.MAX_CONTEXT_CHARS] if context_text else ""

    # 3. Assemble User Message Prompt
    user_prompt_parts = []
    if formatted_history:
        user_prompt_parts.append(f"--- LỊCH SỬ HỘI THOẠI GẦN ĐÂY ---\n{formatted_history}\n")
    
    if truncated_context:
        user_prompt_parts.append(f"--- CƠ SỞ TRI THỨC (RETRIEVED CONTEXT) ---\n{truncated_context}\n")

    if weather_context:
        user_prompt_parts.append(f"--- THÔNG TIN THỜI TIẾT THỜI GIAN THỰC (WEATHER CONTEXT) ---\n{weather_context}\n")

    user_prompt_parts.append(f"--- CÂU HỎI HIỆN TẠI ---\n{query}")

    full_user_prompt = "\n".join(user_prompt_parts)
    logger.info(f"[LLM Service] Assembled Prompt Character Count: {len(full_user_prompt)}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": full_user_prompt}
    ]

    # Khi có nhà cung cấp dự phòng thì không đợi lâu ở nhà cung cấp hiện tại: chuyển nhanh sang mục tiếp theo
    retries = settings.GROQ_MAX_RETRIES if len(chain) == 1 else min(settings.GROQ_MAX_RETRIES, 1)

    first_error: Optional[HTTPException] = None
    for provider in chain:
        try:
            answer = await _complete_with(provider, messages, retries)
            if provider is not chain[0]:
                logger.warning("[LLM Service] Answered by fallback %s:%s", provider.name, provider.model)
            return answer
        except HTTPException as err:
            first_error = first_error or err
            logger.warning("[LLM Service] %s:%s failed (%s); trying next provider",
                           provider.name, provider.model, err.status_code)
    assert first_error is not None
    raise first_error
