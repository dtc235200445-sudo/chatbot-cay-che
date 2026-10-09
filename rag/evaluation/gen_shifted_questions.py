"""
Sinh bộ câu hỏi "lệch từ vựng" để kiểm tra thiên lệch của bộ 1000 câu (câu hỏi sinh từ chính chunk nên dùng lại từ ngữ tài liệu,
có lợi cho tìm kiếm theo từ khóa).

Mỗi chunk được yêu cầu viết câu hỏi bằng cách diễn đạt đời thường/đồng nghĩa, KHÔNG dùng lại cụm từ đặc trưng của đoạn văn.
Sau đó lọc theo độ trùng từ với chunk và so sánh với độ trùng của bộ 1000 câu gốc.

Model sinh: openai/gpt-oss-20b (khác model sinh câu trả lời chính để không tranh hạn mức).
Chạy: python -m rag.evaluation.gen_shifted_questions
"""
import json
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import openai

from backend.config import settings
from rag.evaluation.run_qa1000_retrieval import DATASET_PATH
from rag.text_utils import VI_STOPWORDS, normalize_text

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent / "shifted_questions.json"
MODEL = "openai/gpt-oss-20b"
N_CHUNKS = 90
SEED = 20260924
MAX_OVERLAP = 0.5

PROMPT = """Bạn giúp tạo bộ câu hỏi kiểm thử cho chatbot về cây chè. Dưới đây là một đoạn tài liệu.

ĐOẠN TÀI LIỆU:
\"\"\"{content}\"\"\"

Hãy viết đúng 2 câu hỏi tiếng Việt mà người nông dân hoặc sinh viên có thể hỏi và đoạn tài liệu này trả lời được.
Yêu cầu bắt buộc:
- Diễn đạt bằng lời đời thường, dùng từ đồng nghĩa hoặc mô tả gián tiếp; KHÔNG chép lại các thuật ngữ, cụm từ đặc trưng, con số có trong đoạn tài liệu.
- Không nhắc "theo tài liệu", "đoạn văn", "trong bài".
- Mỗi câu hỏi ngắn (dưới 25 từ), hỏi về nội dung chính của đoạn.
Chỉ trả về JSON dạng: {{"questions": ["...", "..."]}}"""


def content_words(text: str):
    words = re.findall(r"\w+", normalize_text(text))
    return {w for w in words if w not in VI_STOPWORDS and len(w) > 2}


def overlap(question: str, passage: str) -> float:
    q = content_words(question)
    return len(q & content_words(passage)) / len(q) if q else 0.0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = [json.loads(l) for l in DATASET_PATH.open(encoding="utf-8")]
    rag_rows = [r for r in rows if r["dataset"] != "Tea_Regions_Project_Config"]
    orig_overlap = [overlap(r["question"], r["reference_context"]) for r in rag_rows]

    by_ds = defaultdict(dict)
    for r in rag_rows:
        by_ds[r["dataset"]][r["source_chunk_id"]] = r["reference_context"]
    rng = random.Random(SEED)
    total = sum(len(v) for v in by_ds.values())
    picked = []
    for ds, chunks in sorted(by_ds.items()):
        k = max(2, round(N_CHUNKS * len(chunks) / total))
        ids = sorted(chunks)
        rng.shuffle(ids)
        picked += [(ds, cid, chunks[cid]) for cid in ids[:k]]
    print(f"{len(picked)} chunk được chọn", flush=True)

    done = {}
    if OUT.exists():
        done = {q["chunk_id"]: q for q in json.loads(OUT.read_text(encoding="utf-8"))["by_chunk"] if q.get("questions")}
    client = openai.OpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL, max_retries=2, timeout=60)

    for i, (ds, cid, content) in enumerate(picked, 1):
        if cid in done:
            continue
        for attempt in range(5):
            try:
                res = client.chat.completions.create(
                    model=MODEL, temperature=0.7, max_tokens=1500, reasoning_effort="low",
                    messages=[{"role": "user", "content": PROMPT.format(content=content[:2500])}],
                )
                text = res.choices[0].message.content or ""
                m = re.search(r"\{.*\}", text, flags=re.S)
                qs = json.loads(m.group(0))["questions"] if m else []
                break
            except openai.RateLimitError as err:
                if "per day" in str(err).lower():
                    print("DỪNG: hết hạn mức ngày", flush=True)
                    qs = None
                    break
                time.sleep(15 * (attempt + 1))
                qs = []
            except Exception as err:  # noqa: BLE001
                print("lỗi:", str(err)[:100], flush=True)
                time.sleep(5)
                qs = []
        if qs is None:
            break
        done[cid] = {"chunk_id": cid, "dataset": ds, "questions": [q for q in qs if isinstance(q, str)][:2]}
        OUT.write_text(json.dumps({"model": MODEL, "by_chunk": list(done.values())}, ensure_ascii=False, indent=1), encoding="utf-8")
        if i % 10 == 0:
            print(f"  {i}/{len(picked)}", flush=True)

    chunks_text = {cid: text for ds in by_ds.values() for cid, text in ds.items()}
    items = []
    for rec in done.values():
        for q in rec["questions"]:
            ov = overlap(q, chunks_text[rec["chunk_id"]])
            items.append({"question": q, "source_chunk_id": rec["chunk_id"], "dataset": rec["dataset"], "overlap": round(ov, 3)})
    kept = [it for it in items if it["overlap"] <= MAX_OVERLAP]
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    summary = {
        "model": MODEL, "n_chunks": len(done), "n_generated": len(items), "n_kept": len(kept), "max_overlap": MAX_OVERLAP,
        "mean_overlap_original_928": round(mean(orig_overlap), 3),
        "mean_overlap_generated": round(mean([i["overlap"] for i in items]), 3),
        "mean_overlap_kept": round(mean([i["overlap"] for i in kept]), 3),
    }
    OUT.write_text(json.dumps({"summary": summary, "by_chunk": list(done.values()), "questions": kept}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
