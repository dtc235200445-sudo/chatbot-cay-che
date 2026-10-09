"""
Đánh giá tầng CÂU TRẢ LỜI và END-TO-END theo các chỉ số của Ragas, cho Tea AI và RAG thường.

Tầng câu trả lời (model chấm khác họ với model sinh):
  - Faithfulness          : tách câu trả lời thành các mệnh đề; tỉ lệ mệnh đề được NGỮ CẢNH truy xuất xác nhận.
  - Response Relevancy    : model chấm chỉ đọc câu trả lời và đoán 3 câu hỏi mà nó trả lời; điểm = cosine trung bình
                            (embedding bkai) giữa các câu đoán và câu hỏi thật, bằng 0 nếu câu trả lời né tránh.
  - Factual Correctness   : so với ĐÁP ÁN CHUẨN. Precision = tỉ lệ mệnh đề của câu trả lời được đáp án chuẩn xác nhận;
                            Recall = tỉ lệ ý chính của đáp án chuẩn được câu trả lời nêu; F1.
End-to-end:
  - Answer Accuracy       : tỉ lệ câu có đáp án được chấm "đúng" (và "đúng hoặc đúng một phần"), từ chối nhầm tính là sai.
  - No-answer accuracy    : 24 câu thiếu dữ liệu + 12 câu ngoài phạm vi (eval_set.json): tỉ lệ từ chối đúng, không bịa số.
  - Latency, Cost/query   : chạy lại toàn bộ luồng trên LAT_N câu, đo riêng thời gian truy xuất và LLM, lấy số token từ API.
  - Human evaluation      : không tự làm được; dùng phiếu docs/phieu_cham_tay_cap_tra_loi.csv + human_agreement.py.

Câu hỏi: toàn bộ câu semantic_factual thuộc kho RAG trong lượt chạy Tea AI 150 câu (114 câu), KHÔNG lọc theo việc Tea AI
có trả lời hay không (bộ 67 cặp cũ chỉ lấy câu Tea AI đã trả lời nên có lợi cho Tea AI). Dùng lại câu trả lời đã sinh
(gpt-oss-120b); chỉ sinh thêm phần RAG thường còn thiếu. Kết quả lưu từng bước, chạy lại để tiếp tục khi hết hạn mức.

Chạy: python -m backend.evaluation.ragas_style_eval [--lat-n 20] [--pause 1]
"""
import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import openai
from openai import AsyncOpenAI

from backend.config import settings
from backend.evaluation.answer_eval import extract_numbers, is_refusal
from backend.evaluation.qa1000_answer_eval import DATASET_PATH, GENERATOR_MODEL, JUDGE_MODEL
from backend.evaluation.qa1000_vanilla_answer_eval import TOP_K, VANILLA_EMBEDDING, VANILLA_SYSTEM, refused_broad
from backend.services.assistant_service import get_default_retriever
from backend.services.llm_service import SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parent.parent.parent
RUNS = Path(__file__).resolve().parent / "runs"
TEA_RUN = RUNS / "qa1000_answer_eval_20260923_163333_repaired_repaired_repaired.json"
VANILLA_RUN = RUNS / "vanilla_answer_eval.json"
STATE = RUNS / "ragas_style_eval.json"
REPORT = ROOT / "docs" / "RAG_ANSWER_E2E_EVALUATION.md"
EVAL_SET = ROOT / "rag" / "evaluation" / "eval_set.json"
REFUSAL_TEXT = "Hiện tại cơ sở tri thức chưa tìm thấy nguồn thông tin đủ phù hợp để giải đáp chính xác câu hỏi này."
# Giá Groq (USD / 1 triệu token), gpt-oss-120b, không tính giảm giá cache/batch.
PRICE_IN, PRICE_OUT = 0.15, 0.60
N_BOOT, SEED = 2000, 20260926
# Groq giới hạn model chấm 1.000 token đầu ra mỗi phút; max_tokens lớn hơn bị từ chối ngay.
JUDGE_MAX_FACT, JUDGE_MAX_REL = 950, 300
SYSTEMS = ("tea", "vanilla")
LABEL = {"tea": "Tea AI", "vanilla": "RAG thường"}

FACT_PROMPT = """Bạn là người chấm câu trả lời của chatbot hỏi đáp về cây chè. Chỉ dựa vào văn bản được cung cấp, không dùng kiến thức ngoài.

CÂU HỎI:
{question}

NGỮ CẢNH CHATBOT ĐÃ DÙNG:
{context}

ĐÁP ÁN CHUẨN:
{reference}

CÁC Ý CHÍNH CỦA ĐÁP ÁN CHUẨN (đánh số):
{key_points}

CÂU TRẢ LỜI CỦA CHATBOT:
{answer}

Việc cần làm:
1. Tách CÂU TRẢ LỜI thành các mệnh đề độc lập, mỗi mệnh đề một thông tin (bỏ lời chào, câu dẫn), tối đa 15 mệnh đề
   (gộp các ý nhỏ cùng loại). Trường "text" chỉ ghi TÓM TẮT mệnh đề trong tối đa 8 từ. Với mỗi mệnh đề:
   "in_context": true nếu NGỮ CẢNH xác nhận mệnh đề, false nếu ngữ cảnh không nói hoặc nói khác.
   "in_reference": true nếu ĐÁP ÁN CHUẨN xác nhận mệnh đề, false nếu đáp án chuẩn không nói hoặc nói khác.
2. "key_points_covered": với từng ý chính theo đúng thứ tự, true nếu câu trả lời có nêu ý đó (dù diễn đạt khác).
3. "verdict": "đúng" nếu câu trả lời nêu đúng nội dung chính của đáp án chuẩn và không có thông tin sai;
   "một phần" nếu đúng nhưng thiếu ý quan trọng hoặc lẫn thông tin sai nhỏ; "sai" nếu sai, trái ngược hoặc không trả lời.

Chỉ trả JSON gọn, không giải thích, không xuống dòng thừa:
{{"statements": [{{"text": "...", "in_context": true, "in_reference": true}}], "key_points_covered": [true, false], "verdict": "đúng"}}"""

RELEVANCY_PROMPT = """Dưới đây là câu trả lời của một chatbot về cây chè. Hãy viết 3 câu hỏi tiếng Việt khác nhau mà câu trả lời này đang trả lời.
Đồng thời cho biết câu trả lời có né tránh không: "noncommittal": 1 nếu câu trả lời nói không biết, không có thông tin hoặc trả lời mập mờ; 0 nếu trả lời cụ thể.

CÂU TRẢ LỜI:
{answer}

Chỉ trả JSON: {{"questions": ["...", "...", "..."], "noncommittal": 0}}"""


class QuotaExhausted(RuntimeError):
    pass


# ------------------------------------------------------------------ gọi API
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL, max_retries=0, timeout=90)


async def call_llm(model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> Dict[str, Any]:
    """Trả {text, prompt_tokens, completion_tokens, seconds}. Thử lại khi quá tần suất; dừng hẳn khi hết hạn mức ngày."""
    kwargs: Dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if model.startswith("openai/gpt-oss") and settings.GROQ_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.GROQ_REASONING_EFFORT
    client, delay = _client(), 4.0
    for _ in range(12):
        try:
            t0 = time.perf_counter()
            res = await asyncio.wait_for(client.chat.completions.create(**kwargs), 150)  # chặn kết nối treo (máy ngủ, mất mạng)
            text = (res.choices[0].message.content or "").strip()
            if not text:  # model suy luận dùng hết token cho phần suy nghĩ
                kwargs["max_tokens"] = max_tokens * 2
                res = await asyncio.wait_for(client.chat.completions.create(**kwargs), 150)  # chặn kết nối treo (máy ngủ, mất mạng)
                text = (res.choices[0].message.content or "").strip()
            u = res.usage
            return {"text": text, "seconds": time.perf_counter() - t0,
                    "prompt_tokens": getattr(u, "prompt_tokens", None), "completion_tokens": getattr(u, "completion_tokens", None)}
        except openai.RateLimitError as err:
            m = str(err).lower()
            if "per day" in m or "tpd" in m or "rpd" in m:
                raise QuotaExhausted(str(err)[:200])
            if "request too large" in m:
                raise RuntimeError(str(err)[:200])
            # "try again in 1m2.5s", "22.5s" hoặc "600ms" (không được đọc "600ms" thành 600 phút)
            wait = re.search(r"try again in\s+(?:(\d+)m(?!s))?\s*(?:(\d+(?:\.\d+)?)(ms|s))?", m)
            if wait and any(wait.groups()):
                print(f"    chờ giới hạn tần suất: {m[m.find('on_demand'):m.find('need more')]}", flush=True)
                secs = float(wait.group(2) or 0) / (1000 if wait.group(3) == "ms" else 1)
                await asyncio.sleep(min(int(wait.group(1) or 0) * 60 + secs + 1, 300))
                continue
        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError, asyncio.TimeoutError) as err:
            print(f"    lỗi kết nối, thử lại: {type(err).__name__}", flush=True)
        await asyncio.sleep(delay)
        delay = min(delay * 2, 60)
    raise RuntimeError("hết số lần thử")


def parse_json(raw: str) -> Optional[Dict[str, Any]]:
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return None


# ------------------------------------------------------------------ dữ liệu và hai hệ thống
class Systems:
    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.tea = get_default_retriever()
        self.embed = self.tea.vector_store._engine()  # bkai, dùng cho Response Relevancy
        self.chunks = json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.v_model = SentenceTransformer(VANILLA_EMBEDDING)
        self.v_vecs = self.v_model.encode([c["content"] for c in self.chunks], normalize_embeddings=True, show_progress_bar=False)

    def tea_retrieve(self, q: str) -> Dict[str, Any]:
        r = self.tea.retrieve(q, top_k=TOP_K)
        return {"relevant": r["is_relevant"], "context": r["context_text"] if r["is_relevant"] else ""}

    def vanilla_ids(self, q: str) -> List[str]:
        sims = self.v_model.encode([q], normalize_embeddings=True, show_progress_bar=False)[0] @ self.v_vecs.T
        return [self.chunks[j]["chunk_id"] for j in np.argsort(-sims)[:TOP_K]]

    def vanilla_context(self, ids: List[str]) -> str:
        return "\n\n".join(self.by_id[i]["content"] for i in ids)[: settings.MAX_CONTEXT_CHARS]


def tea_messages(q: str, context: str) -> List[Dict[str, str]]:
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"--- CƠ SỞ TRI THỨC (RETRIEVED CONTEXT) ---\n{context[: settings.MAX_CONTEXT_CHARS]}\n\n--- CÂU HỎI HIỆN TẠI ---\n{q}"}]


def vanilla_messages(q: str, context: str) -> List[Dict[str, str]]:
    return [{"role": "system", "content": VANILLA_SYSTEM},
            {"role": "user", "content": f"Ngữ cảnh:\n{context}\n\nCâu hỏi: {q}\n\nTrả lời:"}]


def key_points(row) -> List[str]:
    kp = row.get("answer_key_points") or []
    return json.loads(kp) if isinstance(kp, str) else kp


def save(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ các bước
async def build_answers(state, rows, sysm, pause):
    """Câu trả lời của hai hệ thống trên bộ câu có đáp án; dùng lại kết quả cũ, chỉ sinh phần RAG thường còn thiếu."""
    tea_old = {r["id"]: r for r in json.loads(TEA_RUN.read_text(encoding="utf-8"))["records"]}
    van_old = {r["id"]: r for r in json.loads(VANILLA_RUN.read_text(encoding="utf-8"))["records"]}
    ans = state.setdefault("answers", {})
    for row in rows:
        i, q = row["id"], row["question"]
        if f"tea|{i}" not in ans:
            t = tea_old[i]
            ctx = sysm.tea_retrieve(q)
            ans[f"tea|{i}"] = {"answer": t["answer"], "context": ctx["context"],
                               "refused": bool(t["refused"] or not t["gate_relevant"]), "source": "lượt 23/09"}
        if f"vanilla|{i}" not in ans:
            if i in van_old and van_old[i].get("answer") and not van_old[i]["answer"].startswith("[LỖI"):
                v = van_old[i]
                ans[f"vanilla|{i}"] = {"answer": v["answer"], "context": sysm.vanilla_context(v["retrieved_ids"]),
                                       "refused": refused_broad(v["answer"]), "source": "lượt 24-25/09"}
            else:
                ids = sysm.vanilla_ids(q)
                ctx = sysm.vanilla_context(ids)
                out = await call_llm(GENERATOR_MODEL, vanilla_messages(q, ctx), 0.2, settings.GROQ_MAX_TOKENS)
                ans[f"vanilla|{i}"] = {"answer": out["text"], "context": ctx, "refused": refused_broad(out["text"]), "source": "sinh mới"}
                save(state)
                print(f"  sinh RAG thường {i}", flush=True)
                await asyncio.sleep(pause)
    save(state)


async def judge_all(state, rows, sysm, pause):
    ans, jd = state["answers"], state.setdefault("judge", {})
    for n, row in enumerate(rows, 1):
        for s in SYSTEMS:
            key = f"{s}|{row['id']}"
            if key in jd and (jd[key]["refused"] or (jd[key].get("fact") and jd[key].get("rel"))):
                continue  # đã chấm xong; lần chấm lỗi JSON thì chấm lại
            a = ans[key]
            if a["refused"]:  # từ chối nhầm: không có mệnh đề để chấm
                jd[key] = {"refused": True}
                continue
            kps = key_points(row)
            try:
                fact = parse_json((await call_llm(JUDGE_MODEL, [{"role": "user", "content": FACT_PROMPT.format(
                    question=row["question"], context=a["context"] or "(trống)", reference=row["expected_answer"],
                    key_points="\n".join(f"{k + 1}. {p}" for k, p in enumerate(kps)), answer=a["answer"])}], 0, JUDGE_MAX_FACT))["text"])
                rel = parse_json((await call_llm(JUDGE_MODEL, [{"role": "user", "content": RELEVANCY_PROMPT.format(answer=a["answer"])}], 0, JUDGE_MAX_REL))["text"])
            except RuntimeError as err:  # lỗi riêng một câu: bỏ qua, lần chạy sau chấm lại
                print(f"  lỗi {key}: {err}", flush=True)
                continue
            jd[key] = {"refused": False, "fact": fact, "rel": rel}
            save(state)
            print(f"  [{n}/{len(rows)}] chấm {key}", flush=True)
            await asyncio.sleep(pause)


async def no_answer(state, sysm, pause):
    """12 câu ngoài phạm vi: Tea AI qua cổng (nếu lọt cổng thì sinh bằng prompt sản phẩm), RAG thường luôn sinh."""
    oos = state.setdefault("oos", {})
    qs = [q for q in json.loads(EVAL_SET.read_text(encoding="utf-8"))["queries"] if q["type"] != "in_domain"]
    for q in qs:
        for s in SYSTEMS:
            key = f"{s}|{q['id']}"
            if key in oos:
                continue
            if s == "tea":
                r = sysm.tea_retrieve(q["query"])
                text = (await call_llm(GENERATOR_MODEL, tea_messages(q["query"], r["context"]), 0.2, settings.GROQ_MAX_TOKENS))["text"] \
                    if r["relevant"] else REFUSAL_TEXT
            else:
                ctx = sysm.vanilla_context(sysm.vanilla_ids(q["query"]))
                text = (await call_llm(GENERATOR_MODEL, vanilla_messages(q["query"], ctx), 0.2, settings.GROQ_MAX_TOKENS))["text"]
                await asyncio.sleep(pause)
            oos[key] = {"query": q["query"], "type": q["type"], "answer": text, "refused": refused_broad(text),
                        "has_numbers": bool(extract_numbers(text))}
            save(state)


async def latency(state, rows, sysm, lat_n, pause):
    """Chạy lại toàn bộ luồng trên lat_n câu, đo thời gian và số token thật."""
    lat = state.setdefault("latency", {})
    step = max(1, len(rows) // lat_n)
    for row in rows[::step][:lat_n]:
        q = row["question"]
        for s in SYSTEMS:
            key = f"{s}|{row['id']}"
            if key in lat:
                continue
            t0 = time.perf_counter()
            if s == "tea":
                r = sysm.tea_retrieve(q)
                t_ret = time.perf_counter() - t0
                out = await call_llm(GENERATOR_MODEL, tea_messages(q, r["context"]), 0.2, settings.GROQ_MAX_TOKENS) if r["relevant"] \
                    else {"seconds": 0.0, "prompt_tokens": 0, "completion_tokens": 0}
            else:
                ctx = sysm.vanilla_context(sysm.vanilla_ids(q))
                t_ret = time.perf_counter() - t0
                out = await call_llm(GENERATOR_MODEL, vanilla_messages(q, ctx), 0.2, settings.GROQ_MAX_TOKENS)
            lat[key] = {"retrieval_s": t_ret, "llm_s": out["seconds"], "total_s": t_ret + out["seconds"],
                        "prompt_tokens": out["prompt_tokens"], "completion_tokens": out["completion_tokens"]}
            save(state)
            await asyncio.sleep(pause)


# ------------------------------------------------------------------ tính chỉ số
def scores(state, rows, sysm):
    ans, jd = state["answers"], state["judge"]
    per = {s: [] for s in SYSTEMS}
    for row in rows:
        q_vec = None
        for s in SYSTEMS:
            key = f"{s}|{row['id']}"
            j = jd.get(key)
            if j is None:
                per[s].append(None)
                continue
            if j["refused"]:
                per[s].append({"refused": True, "faith": None, "rel": 0.0, "fc_p": None, "fc_r": 0.0, "fc_f1": 0.0,
                               "correct": 0.0, "lenient": 0.0, "numbers_unsupported": False})
                continue
            f, r = j.get("fact") or {}, j.get("rel") or {}
            st = [x for x in f.get("statements") or [] if isinstance(x, dict)]
            faith = sum(x.get("in_context") is True for x in st) / len(st) if st else None
            fc_p = sum(x.get("in_reference") is True for x in st) / len(st) if st else None
            cov, n_kp = f.get("key_points_covered") or [], len(key_points(row))
            fc_r = sum(c is True for c in cov) / n_kp if n_kp and len(cov) == n_kp else None
            fc_f1 = (2 * fc_p * fc_r / (fc_p + fc_r) if fc_p + fc_r else 0.0) if fc_p is not None and fc_r is not None else None
            gen_q = [x for x in (r.get("questions") or []) if isinstance(x, str) and x.strip()]
            rel = None
            if gen_q:
                if q_vec is None:
                    q_vec = sysm.embed.encode([row["question"]])[0]
                rel = float(np.mean(sysm.embed.encode(gen_q) @ q_vec)) * (0 if r.get("noncommittal") in (1, "1", True) else 1)
            v = str(f.get("verdict", "")).strip().lower()
            per[s].append({"refused": False, "faith": faith, "rel": rel, "fc_p": fc_p, "fc_r": fc_r, "fc_f1": fc_f1,
                           "correct": float(v == "đúng"), "lenient": float(v in ("đúng", "một phần", "đúng một phần")),
                           "judge_ok": bool(st)})
    return per


def mean_of(vals):
    vals = [v for v in vals if v is not None]
    return (float(np.mean(vals)), len(vals)) if vals else (None, 0)


def paired_ci(a, b, rng):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 5:
        return None
    x, y = np.array(pairs, float).T
    idx = rng.integers(0, len(x), (N_BOOT, len(x)))
    d = x[idx].mean(1) - y[idx].mean(1)
    return float((x - y).mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), len(x)


def render(state, rows, per, abstain):
    rng = np.random.default_rng(SEED)
    f = lambda v, d=3: "—" if v is None else f"{v:.{d}f}"
    L = ["# Đánh giá câu trả lời và end-to-end: Tea AI so với RAG thường\n",
         f"Model sinh `{GENERATOR_MODEL}`, model chấm `{JUDGE_MODEL}` (khác họ). Bộ câu có đáp án: **{len(rows)} câu** "
         "semantic_factual thuộc kho RAG (mẫu 150 câu của bộ 1000 câu), không lọc theo kết quả của hệ thống nào.\n",
         "## 1. Tầng câu trả lời\n",
         "| Chỉ số | Tea AI | RAG thường | Chênh lệch Tea − RAG thường [KTC 95%] |", "|---|---|---|---|"]
    metrics = [("Faithfulness (chỉ câu không từ chối)", "faith"), ("Response Relevancy", "rel"),
               ("Factual Correctness: Precision (chỉ câu không từ chối)", "fc_p"), ("Factual Correctness: Recall", "fc_r"),
               ("Factual Correctness: F1", "fc_f1")]
    summary = {}
    for name, k in metrics:
        vals = {s: [p[k] if p else None for p in per[s]] for s in SYSTEMS}
        m = {s: mean_of(vals[s]) for s in SYSTEMS}
        ci = paired_ci(vals["tea"], vals["vanilla"], rng)
        summary[k] = {s: m[s][0] for s in SYSTEMS}
        L.append(f"| {name} | {f(m['tea'][0])} (n={m['tea'][1]}) | {f(m['vanilla'][0])} (n={m['vanilla'][1]}) | "
                 + (f"{ci[0]:+.3f} [{ci[1]:+.3f}, {ci[2]:+.3f}], {ci[3]} cặp" if ci else "—") + " |")
    L.append("\nCâu bị từ chối nhầm: Response Relevancy = 0, Factual Correctness Recall/F1 = 0; không có mệnh đề nên không tính "
             "Faithfulness và Precision (số n cho biết số câu được tính).\n")

    L += ["## 2. End-to-end\n", "### 2.1. Độ chính xác câu trả lời\n",
          "| Chỉ số | Tea AI | RAG thường |", "|---|---|---|"]
    for name, k in (("Trả lời đúng", "correct"), ("Đúng hoặc đúng một phần", "lenient")):
        L.append(f"| {name} | " + " | ".join(f"{f((mean_of([p[k] if p else None for p in per[s]])[0] or 0) * 100, 1)}%" for s in SYSTEMS) + " |")
    L.append("| Từ chối nhầm câu có đáp án | " + " | ".join(
        f"{sum(1 for p in per[s] if p and p['refused'])}/{sum(1 for p in per[s] if p)}" for s in SYSTEMS) + " |")
    ci = paired_ci([p["correct"] if p else None for p in per["tea"]], [p["correct"] if p else None for p in per["vanilla"]], rng)
    if ci:
        L.append(f"\nChênh lệch tỉ lệ trả lời đúng: {ci[0] * 100:+.1f} điểm phần trăm [KTC 95% {ci[1] * 100:+.1f}, {ci[2] * 100:+.1f}].\n")

    L += ["### 2.2. Khi tài liệu không có thông tin (No-answer accuracy)\n",
          "| Bộ câu | Tea AI: từ chối đúng | Tea AI: bịa số | RAG thường: từ chối đúng | RAG thường: bịa số |", "|---|---|---|---|---|"]
    L.append(f"| 24 câu thiếu dữ liệu (vùng chè) | {abstain['tea'][0]}/{abstain['n']} | {abstain['tea'][1]} | "
             f"{abstain['vanilla'][0]}/{abstain['n']} | {abstain['vanilla'][1]} |")
    oos = state.get("oos", {})
    n_oos = len({k.split('|')[1] for k in oos})
    if n_oos:
        cnt = {s: (sum(v["refused"] for k, v in oos.items() if k.startswith(s)),
                   sum((not v["refused"]) and v["has_numbers"] for k, v in oos.items() if k.startswith(s))) for s in SYSTEMS}
        L.append(f"| {n_oos} câu ngoài phạm vi (eval_set.json) | {cnt['tea'][0]}/{n_oos} | {cnt['tea'][1]} | {cnt['vanilla'][0]}/{n_oos} | {cnt['vanilla'][1]} |")
        tot = {s: abstain[s][0] + cnt[s][0] for s in SYSTEMS}
        L.append(f"| **Tổng** | **{tot['tea']}/{abstain['n'] + n_oos}** | | **{tot['vanilla']}/{abstain['n'] + n_oos}** | |")
    L.append("\n\"Bịa số\" = không từ chối mà câu trả lời có số liệu cụ thể.\n")

    lat = state.get("latency", {})
    if lat:
        L += ["### 2.3. Thời gian chờ và chi phí mỗi câu hỏi\n",
              f"Chạy lại toàn bộ luồng trên {len(lat) // 2} câu, gọi API Groq thật. Giá gpt-oss-120b trên Groq: "
              f"${PRICE_IN}/1 triệu token vào, ${PRICE_OUT}/1 triệu token ra (token ra gồm cả phần suy luận của model).\n",
              "| Chỉ số | Tea AI | RAG thường |", "|---|---|---|"]
        g = {s: [v for k, v in lat.items() if k.startswith(s)] for s in SYSTEMS}
        row_ = lambda name, fn: L.append(f"| {name} | " + " | ".join(fn(g[s]) for s in SYSTEMS) + " |")
        row_("Truy xuất, trung vị (ms)", lambda v: f"{np.median([x['retrieval_s'] for x in v]) * 1000:.0f}")
        row_("LLM, trung vị (giây)", lambda v: f"{np.median([x['llm_s'] for x in v]):.2f}")
        row_("Tổng, trung vị (giây)", lambda v: f"{np.median([x['total_s'] for x in v]):.2f}")
        row_("Tổng, P90 (giây)", lambda v: f"{np.percentile([x['total_s'] for x in v], 90):.2f}")
        row_("Token vào, trung bình", lambda v: f"{np.mean([x['prompt_tokens'] or 0 for x in v]):.0f}")
        row_("Token ra, trung bình", lambda v: f"{np.mean([x['completion_tokens'] or 0 for x in v]):.0f}")
        cost = lambda v: np.mean([(x["prompt_tokens"] or 0) * PRICE_IN / 1e6 + (x["completion_tokens"] or 0) * PRICE_OUT / 1e6 for x in v])
        row_("Chi phí mỗi câu (USD)", lambda v: f"{cost(v):.5f}")
        row_("Chi phí 1.000 câu (USD)", lambda v: f"{cost(v) * 1000:.2f}")
        L.append("\nThời gian LLM phụ thuộc tải của Groq tại lúc đo; nên so sánh hai hệ thống trong cùng lượt chạy, không đọc như con số cố định. "
                 "Chi phí chưa gồm model chấm (chỉ dùng khi đánh giá).\n")

    L += ["### 2.4. Người chấm (Human evaluation)\n",
          "Chưa có kết quả. Phiếu `docs/phieu_cham_tay_cap_tra_loi.csv` (30 cặp, ẩn tên hệ thống: A/B) chưa được điền. "
          "Sau khi điền, chạy `python -m backend.evaluation.human_agreement` để có điểm theo người và mức đồng thuận với model chấm.\n"]

    L += ["## 3. Theo loại câu hỏi (Factual Correctness F1 / Faithfulness)\n", "| Loại | N | Tea AI | RAG thường |", "|---|---|---|---|"]
    for qt in sorted({r["question_type"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["question_type"] == qt]
        cell = lambda s: f"{f(mean_of([per[s][i]['fc_f1'] if per[s][i] else None for i in idx])[0], 2)} / " \
                         f"{f(mean_of([per[s][i]['faith'] if per[s][i] else None for i in idx])[0], 2)}"
        L.append(f"| {qt} | {len(idx)} | {cell('tea')} | {cell('vanilla')} |")

    L += ["\n## Lưu ý khi diễn giải\n",
          "- Các chỉ số làm theo định nghĩa của Ragas nhưng do một model chấm duy nhất thực hiện; chưa đối chiếu với người chấm.",
          "- Faithfulness chỉ đo câu trả lời có bám ngữ cảnh không. RAG thường lấy sai tài liệu nhưng vẫn có thể có Faithfulness cao "
          "(bám đúng tài liệu sai), vì vậy cần đọc cùng Factual Correctness.",
          "- Câu trả lời của Tea AI được sinh ngày 23/09; ngữ cảnh được truy xuất lại khi chấm (truy xuất tất định, kho không đổi).",
          "- Giữa chừng, prompt chấm được sửa để model chấm ghi mệnh đề ngắn và gộp tối đa 15 mệnh đề/câu (Groq giới hạn "
          "1.000 token ra mỗi phút làm kết quả chấm của câu trả lời dài bị cắt cụt). Khoảng 150/228 câu được chấm bằng prompt cũ; "
          "các chỉ số là tỉ lệ nên ảnh hưởng nhỏ, nhưng câu trả lời rất dài có thể bị chấm thô hơn.",
          "- Mẫu có đáp án là mẫu con 150 câu của bộ 1000 câu, được sinh từ chính tài liệu nên thuận lợi cho khâu truy xuất."]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return summary


def abstain_counts():
    tea = [r for r in json.loads(TEA_RUN.read_text(encoding="utf-8"))["records"] if r["grading_mode"] == "abstain_no_data"]
    van = [r for r in json.loads(VANILLA_RUN.read_text(encoding="utf-8"))["records"] if r["grading_mode"] == "abstain_no_data"]
    return {"n": len(tea),
            "tea": (sum(bool(r["refused"] or not r["gate_relevant"]) for r in tea), sum(bool(r.get("abstain_violation")) for r in tea)),
            "vanilla": (sum(refused_broad(r["answer"]) for r in van),
                        sum((not refused_broad(r["answer"])) and bool(extract_numbers(r["answer"])) for r in van))}


async def run(lat_n: int, pause: float):
    ds = {json.loads(l)["id"]: json.loads(l) for l in DATASET_PATH.open(encoding="utf-8")}
    tea_old = json.loads(TEA_RUN.read_text(encoding="utf-8"))["records"]
    rows = [ds[r["id"]] for r in tea_old if r["grading_mode"] == "semantic_factual" and r["dataset"] != "Tea_Regions_Project_Config"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    sysm = Systems()
    print(f"{len(rows)} câu có đáp án", flush=True)
    try:
        print("1. câu trả lời", flush=True)
        await build_answers(state, rows, sysm, pause)
        print("2. chấm", flush=True)
        await judge_all(state, rows, sysm, pause)
        print("3. câu ngoài phạm vi", flush=True)
        await no_answer(state, sysm, pause)
        print("4. thời gian và chi phí", flush=True)
        await latency(state, rows, sysm, lat_n, pause)
    except QuotaExhausted as err:
        save(state)
        print(f"DỪNG: hết hạn mức ngày ({err}). Chạy lại lệnh sau để tiếp tục; báo cáo dưới đây là kết quả tạm.", flush=True)
    per = scores(state, rows, sysm)
    render(state, rows, per, abstain_counts())


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lat-n", type=int, default=20)
    p.add_argument("--pause", type=float, default=1.0)
    a = p.parse_args()
    asyncio.run(run(a.lat_n, a.pause))


if __name__ == "__main__":
    main()
