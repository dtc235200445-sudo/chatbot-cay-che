import math
from typing import Dict, List, Sequence, Set


def hit_at_k(ranked_ids: Sequence[str], relevant: Set[str], k: int) -> float:
    return float(any(cid in relevant for cid in ranked_ids[:k]))


def reciprocal_rank(ranked_ids: Sequence[str], relevant: Set[str]) -> float:
    for rank, cid in enumerate(ranked_ids, 1):
        if cid in relevant:
            return 1.0 / rank
    return 0.0


def precision_at_k(ranked_ids: Sequence[str], relevant: Set[str], k: int) -> float:
    return sum(cid in relevant for cid in ranked_ids[:k]) / k


def ndcg_at_k(ranked_ids: Sequence[str], relevant: Set[str], k: int) -> float:
    """nDCG với độ liên quan nhị phân."""
    dcg = sum(1.0 / math.log2(i + 2) for i, cid in enumerate(ranked_ids[:k]) if cid in relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize_ranking(cases: List[Dict], k_values=(1, 3, 5)) -> Dict[str, float]:
    """cases: [{"ranked_ids": [...], "relevant": {...}}] — chỉ gồm câu hỏi thuộc phạm vi."""
    summary = {f"hit@{k}": mean([hit_at_k(c["ranked_ids"], c["relevant"], k) for c in cases]) for k in k_values}
    summary["mrr"] = mean([reciprocal_rank(c["ranked_ids"], c["relevant"]) for c in cases])
    summary["ndcg@3"] = mean([ndcg_at_k(c["ranked_ids"], c["relevant"], 3) for c in cases])
    summary["precision@3"] = mean([precision_at_k(c["ranked_ids"], c["relevant"], 3) for c in cases])
    return summary
