"""
Tổng hợp bảng so sánh tầng ANSWER: Tea AI vs RAG thường trên cùng tập con câu hỏi ghép cặp.

Chạy: python -m backend.evaluation.qa1000_vanilla_answer_report
Ghi: docs/RAG_BASELINE_ANSWER_COMPARISON.md
"""
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from backend.evaluation.qa1000_vanilla_answer_eval import OUT_PATH, TEA_RUN_GLOB, refused_broad

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "docs" / "RAG_BASELINE_ANSWER_COMPARISON.md"
SEED, N_BOOT = 20260924, 2000


def mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def f(v, d=3):
    return "—" if v is None else f"{v:.{d}f}"


def boot_ci(a, b, rng):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a)
    if n < 2:
        return None
    diffs = [a[i].mean() - b[i].mean() for i in (rng.integers(0, n, n) for _ in range(N_BOOT))]
    return float((a - b).mean()), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rng = np.random.default_rng(SEED)
    tea = {r["id"]: r for r in json.loads(Path(glob.glob(TEA_RUN_GLOB)[0]).read_text(encoding="utf-8"))["records"]}
    van = {r["id"]: r for r in json.loads(OUT_PATH.read_text(encoding="utf-8"))["records"]
           if r.get("answer") and not str(r["answer"]).startswith("[LỖI")}
    ids = [i for i in van if i in tea]

    ab = [i for i in ids if van[i]["grading_mode"] == "abstain_no_data"]
    sem = [i for i in ids if van[i]["grading_mode"] == "semantic_factual"]
    sem_ok = [i for i in sem if van[i].get("judge") and tea[i].get("judge")]

    # Từ chối áp dụng cùng một bộ nhận diện rộng cho cả hai hệ thống
    tea_ref = {i: refused_broad(tea[i]["answer"] or "") or not tea[i]["gate_relevant"] for i in ids}
    van_ref = {i: refused_broad(van[i]["answer"]) for i in ids}

    L = ["# So sánh Tea AI với RAG thường (tầng câu trả lời)\n",
         "Cùng model sinh `openai/gpt-oss-120b` (cùng temperature 0.2, max_tokens, reasoning_effort như sản phẩm), cùng model chấm "
         "`qwen/qwen3.8-27b` và cùng prompt chấm. Khác nhau: **Tea AI** = hybrid retrieval + cổng từ chối + prompt ràng buộc "
         "của sản phẩm; **RAG thường** = embedding đa ngữ dense top-3 + prompt chung "
         "(\"trả lời dựa trên ngữ cảnh, nếu không có thì nói không biết\"), không cổng.\n",
         f"Tập con ghép cặp: {len(ids)} câu có kết quả ở cả hai hệ thống ({len(ab)} câu thiếu dữ liệu, {len(sem)} câu có đáp án chuẩn; "
         f"{len(sem_ok)} câu được chấm ở cả hai).\n"]

    L.append("\n## 1. Câu thiếu dữ liệu (abstain_no_data): có từ chối đúng, không bịa số liệu không\n")
    L.append("| Hệ thống | N | Từ chối đúng | Bịa số liệu | Cổng từ chối được kích hoạt |")
    L.append("|---|---|---|---|---|")
    if ab:
        tv = sum(tea_ref[i] for i in ab); vv = sum(van_ref[i] for i in ab)
        tviol = sum(bool(tea[i].get("abstain_violation")) for i in ab)
        vviol = sum(bool(van[i].get("abstain_violation")) for i in ab)
        gate = sum(not tea[i]["gate_relevant"] for i in ab)
        L.append(f"| Tea AI | {len(ab)} | {tv} | {tviol} | {gate}/{len(ab)} |")
        L.append(f"| RAG thường | {len(ab)} | {vv} | {vviol} | không có cổng |")

    L.append("\n## 2. Chất lượng câu trả lời (câu có đáp án chuẩn, chỉ tính câu cả hai đều được chấm)\n")
    L.append("| Hệ thống | N chấm | Correctness (1-5) | Faithfulness | Key point coverage | Số liệu không căn cứ | Độ trễ TB (s) |")
    L.append("|---|---|---|---|---|---|---|")

    def row(name, recs, ids_):
        js = [recs[i]["judge"] for i in ids_]
        unsup = sum(bool(recs[i].get("unsupported_numbers")) for i in ids_)
        lat = mean([recs[i]["latency_s"] for i in ids_])
        return (f"| {name} | {len(ids_)} | {f(mean([j['correctness'] for j in js]), 2)} | {f(mean([j['faithfulness'] for j in js]))} | "
                f"{f(mean([j['key_point_coverage'] for j in js]))} | {unsup} | {f(lat, 1)} |")

    if sem_ok:
        L.append(row("Tea AI", tea, sem_ok))
        L.append(row("RAG thường", van, sem_ok))
        L.append("\nChênh lệch ghép cặp (Tea AI − RAG thường), khoảng tin cậy 95% bằng bootstrap:\n")
        L.append("| Chỉ số | Chênh lệch | KTC 95% |")
        L.append("|---|---|---|")
        for label, key in (("Correctness", "correctness"), ("Faithfulness", "faithfulness"), ("Key point coverage", "key_point_coverage")):
            a = [tea[i]["judge"][key] for i in sem_ok]; b = [van[i]["judge"][key] for i in sem_ok]
            pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
            r = boot_ci([p[0] for p in pairs], [p[1] for p in pairs], rng) if pairs else None
            L.append(f"| {label} | {f(r[0], 3) if r else '—'} | {('[%+.3f, %+.3f]' % (r[1], r[2])) if r else '—'} |")

        L.append("\n### Theo loại câu hỏi (Correctness / Key point coverage)\n")
        L.append("| Loại | N | Tea AI | RAG thường |")
        L.append("|---|---|---|---|")
        for qt in sorted({van[i]["question_type"] for i in sem_ok}):
            sub = [i for i in sem_ok if van[i]["question_type"] == qt]
            g = lambda recs, k: f(mean([recs[i]["judge"][k] for i in sub]), 2 if k == "correctness" else 3)
            L.append(f"| {qt} | {len(sub)} | {g(tea,'correctness')} / {g(tea,'key_point_coverage')} | {g(van,'correctness')} / {g(van,'key_point_coverage')} |")

    L.append("\n## 3. Từ chối nhầm và truy xuất trúng nguồn (câu có đáp án chuẩn)\n")
    L.append("| Hệ thống | N | Từ chối nhầm | Top-3 chứa đúng chunk nguồn |")
    L.append("|---|---|---|---|")
    if sem:
        hit_van = sum(bool(van[i]["hit_source_chunk"]) for i in sem)
        L.append(f"| Tea AI | {len(sem)} | {sum(tea_ref[i] for i in sem)} | (xem `QA1000_RETRIEVAL_RESULTS.md`: Hit@3 0.991) |")
        L.append(f"| RAG thường | {len(sem)} | {sum(van_ref[i] for i in sem)} | {hit_van}/{len(sem)} |")

    L.append("\n## Lưu ý\n")
    L.append("- Tập con nhỏ (chọn đều theo từng loại, không ngẫu nhiên hoàn toàn): dùng để nhìn xu hướng, KTC rộng, không nên coi là kết luận thống kê chắc chắn.")
    L.append("- Cùng một model chấm cho cả hai hệ thống; model chấm có thể có thiên lệch riêng (độ tin cậy của model chấm xem `ANSWER_EVAL_RESULTS.md`).")
    L.append("- \"Từ chối\" được nhận diện bằng cùng một bộ luật rộng cho cả hai hệ thống (câu ngắn nói không có/không biết).")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
