"""
Đo độ bền của truy xuất RAG trước cách gõ thực tế của người dùng (đặc biệt: gõ không dấu trên điện thoại).

Mỗi biến thể biến đổi câu hỏi của bộ đánh giá rồi đo lại xếp hạng (hybrid) và cổng từ chối.

Chạy:  python -m rag.evaluation.robustness --report docs/RAG_ROBUSTNESS_RESULTS.md
"""
import argparse
import random
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rag.evaluation.metrics import summarize_ranking
from rag.evaluation.run_eval import load_eval_set
from rag.retriever import MODE_BM25, MODE_DENSE, MODE_HYBRID, RAGRetriever
from rag.text_utils import fold_diacritics


def swap_typos(text: str, seed: int = 7, word_rate: float = 0.24) -> str:
    """Mô phỏng gõ nhầm: đổi chỗ hai ký tự liền nhau trong một phần các từ dài hơn 3 ký tự (xác định theo seed)."""
    rng = random.Random(seed)
    out = []
    for word in text.split():
        if len(word) > 3 and rng.random() < word_rate:
            i = rng.randrange(len(word) - 1)
            word = word[:i] + word[i + 1] + word[i] + word[i + 2:]
        out.append(word)
    return " ".join(out)


VARIANTS: Dict[str, Callable[[str], str]] = {
    "gốc (có dấu)": lambda q: q,
    "viết thường, bỏ dấu câu": lambda q: re.sub(r"[?!.,]", "", q.lower()),
    "có dấu + gõ nhầm": swap_typos,
    "không dấu": fold_diacritics,
    "không dấu + gõ nhầm": lambda q: swap_typos(fold_diacritics(q)),
}


def evaluate_variant(retriever: RAGRetriever, queries: List[dict], transform: Callable[[str], str]) -> dict:
    result: dict = {}
    for mode in (MODE_DENSE, MODE_BM25, MODE_HYBRID):
        cases = []
        for item in queries:
            if item["type"] != "in_domain":
                continue
            res = retriever.retrieve(transform(item["query"]), top_k=5, mode=mode)
            cases.append({
                "ranked_ids": [c["chunk_id"] for c in res["retrieved_chunks"]],
                "relevant": set(item["relevant_chunk_ids"]),
            })
        result[mode] = summarize_ranking(cases)

    accepted = rejected = n_in = n_out = 0
    for item in queries:
        relevant = retriever.retrieve(transform(item["query"]), top_k=3)["is_relevant"]
        if item["type"] == "in_domain":
            n_in += 1
            accepted += relevant
        else:
            n_out += 1
            rejected += not relevant
    result["gate"] = {"accept_in": accepted / n_in, "reject_out": rejected / n_out}
    return result


def render(results: Dict[str, dict]) -> str:
    lines = [
        "# Độ bền của truy xuất trước cách gõ của người dùng",
        "",
        "Cùng bộ câu hỏi đánh giá, biến đổi cách viết rồi đo lại. `Hit@3 hybrid` là chỉ số chính; hai cột cuối là cổng từ chối.",
        "",
        "| Biến thể câu hỏi | Hit@1 hybrid | Hit@3 hybrid | MRR hybrid | Hit@3 chỉ vector | Hit@3 chỉ BM25 | Nhận đúng câu trong phạm vi | Từ chối đúng câu ngoài phạm vi |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, r in results.items():
        h, g = r[MODE_HYBRID], r["gate"]
        lines.append(
            f"| {name} | {h['hit@1']:.3f} | {h['hit@3']:.3f} | {h['mrr']:.3f} | {r[MODE_DENSE]['hit@3']:.3f} | "
            f"{r[MODE_BM25]['hit@3']:.3f} | {g['accept_in']:.1%} | {g['reject_out']:.1%} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="ghi kết quả ra Markdown")
    args = parser.parse_args()

    queries = load_eval_set()
    retriever = RAGRetriever()
    retriever.load()
    results = {name: evaluate_variant(retriever, queries, fn) for name, fn in VARIANTS.items()}
    text = render(results)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
        print(f"Đã ghi {args.report}")


if __name__ == "__main__":
    main()
