"""
Đánh giá chất lượng truy xuất RAG bằng bộ câu hỏi có gán nhãn (eval_set.json).

Chạy:  python -m rag.evaluation.run_eval            # so sánh dense / bm25 / hybrid
       python -m rag.evaluation.run_eval --report docs/RAG_EVALUATION_RESULTS.md
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rag import config
from rag.evaluation.metrics import summarize_ranking
from rag.retriever import MODE_BM25, MODE_DENSE, MODE_HYBRID, RAGRetriever

EVAL_SET_PATH = Path(__file__).with_name("eval_set.json")
RANKING_K = 5
MODES = (MODE_DENSE, MODE_BM25, MODE_HYBRID)


def load_eval_set(path: Path = EVAL_SET_PATH) -> List[Dict]:
    return json.loads(path.read_text(encoding="utf-8"))["queries"]


def evaluate_ranking(retriever: RAGRetriever, queries: List[Dict], mode: str) -> Dict[str, float]:
    cases = []
    for item in queries:
        if item["type"] != "in_domain":
            continue
        res = retriever.retrieve(item["query"], top_k=RANKING_K, mode=mode)
        cases.append({
            "ranked_ids": [c["chunk_id"] for c in res["retrieved_chunks"]],
            "relevant": set(item["relevant_chunk_ids"]),
        })
    return summarize_ranking(cases)


def evaluate_gate(retriever: RAGRetriever, queries: List[Dict]) -> Dict[str, object]:
    """Cổng từ chối: câu trong phạm vi phải được nhận, câu ngoài phạm vi/thiếu tri thức phải bị từ chối."""
    accepted_in = total_in = rejected_out = total_out = 0
    wrong: List[str] = []
    for item in queries:
        res = retriever.retrieve(item["query"], top_k=config.DEFAULT_TOP_K)
        if item["type"] == "in_domain":
            total_in += 1
            if res["is_relevant"]:
                accepted_in += 1
            else:
                wrong.append(f"[bị từ chối nhầm] {item['query']}")
        else:
            total_out += 1
            if not res["is_relevant"]:
                rejected_out += 1
            else:
                wrong.append(f"[lọt qua cổng] ({item['type']}) {item['query']}")
    return {
        "accept_in_domain": accepted_in / total_in if total_in else 0.0,
        "reject_out_of_scope": rejected_out / total_out if total_out else 0.0,
        "total_in_domain": total_in,
        "total_out_of_scope": total_out,
        "errors": wrong,
    }


def render_markdown(results: Dict[str, Dict[str, float]], gate: Dict[str, object], n_in: int) -> str:
    lines = [
        "# Kết quả đánh giá RAG",
        "",
        f"Bộ câu hỏi: {n_in} câu trong phạm vi + {gate['total_out_of_scope']} câu ngoài phạm vi/thiếu tri thức. "
        f"Cấu hình: alpha={config.HYBRID_ALPHA}, MIN_COSINE={config.MIN_COSINE}, MIN_BM25={config.MIN_BM25}.",
        "",
        "## Chất lượng xếp hạng (câu hỏi trong phạm vi)",
        "",
        "| Phương pháp | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | P@3 |",
        "|---|---|---|---|---|---|---|",
    ]
    for mode, m in results.items():
        lines.append(
            f"| {mode} | {m['hit@1']:.3f} | {m['hit@3']:.3f} | {m['hit@5']:.3f} | "
            f"{m['mrr']:.3f} | {m['ndcg@3']:.3f} | {m['precision@3']:.3f} |"
        )
    lines += [
        "",
        "## Cổng từ chối câu hỏi ngoài cơ sở tri thức",
        "",
        f"- Nhận đúng câu trong phạm vi: {gate['accept_in_domain']:.1%}",
        f"- Từ chối đúng câu ngoài phạm vi/thiếu tri thức: {gate['reject_out_of_scope']:.1%}",
    ]
    if gate["errors"]:
        lines += ["", "Các câu phân loại sai:", ""] + [f"- {e}" for e in gate["errors"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Ghi kết quả ra file Markdown")
    args = parser.parse_args()

    queries = load_eval_set()
    retriever = RAGRetriever()
    results = {mode: evaluate_ranking(retriever, queries, mode) for mode in MODES}
    gate = evaluate_gate(retriever, queries)
    n_in = sum(1 for q in queries if q["type"] == "in_domain")

    report = render_markdown(results, gate, n_in)
    print(report)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"Đã ghi {args.report}")


if __name__ == "__main__":
    main()
