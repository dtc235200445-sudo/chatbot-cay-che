"""
Tổng hợp so sánh Tea AI và RAG thường qua NHIỀU model sinh/chấm.

Nguồn:
  - Cấu hình chính: gpt-oss-120b sinh, qwen3.8-27b chấm (Tea AI: qa1000_answer_eval_*repaired*.json, RAG thường: vanilla_answer_eval.json)
  - Các cấu hình khác: runs/pair_<sinh>__judge_<chấm>.json (qa_pair_eval.py)

Hai cách tính điểm:
  - Có điều kiện: chỉ câu cả hai hệ thống đều được chấm (thiên lệch có lợi cho hệ thống hay từ chối).
  - Đầu-cuối: câu bị từ chối nhầm tính điểm thấp nhất (correctness=1, coverage=0) nên không bỏ sót lỗi từ chối.

Chạy: python -m backend.evaluation.pair_report
Ghi: docs/RAG_MULTI_MODEL_ANSWER_COMPARISON.md và docs/phieu_cham_tay_cap_tra_loi.csv (+ đáp án ẩn)
"""
import csv
import glob
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from backend.evaluation.answer_eval import extract_numbers
from backend.evaluation.qa1000_vanilla_answer_eval import OUT_PATH, TEA_RUN_GLOB, _BROAD_REFUSAL, refused_broad
from backend.evaluation.qa1000_answer_eval import build_sample

ROOT = Path(__file__).resolve().parent.parent.parent
RUNS = Path(__file__).resolve().parent / "runs"
REPORT = ROOT / "docs" / "RAG_MULTI_MODEL_ANSWER_COMPARISON.md"
SHEET = ROOT / "docs" / "phieu_cham_tay_cap_tra_loi.csv"
KEY = ROOT / "docs" / "phieu_cham_tay_dap_an_an.json"
SEED, N_BOOT = 20260924, 2000


def _refused(r):
    """Từ chối theo nghĩa rộng. Với câu thiếu dữ liệu, lời từ chối có thể dài (giải thích ngữ cảnh chỉ có gì) nên xét 200 ký tự đầu."""
    a = r.get("answer") or ""
    if refused_broad(a):
        return True
    return r.get("grading_mode") == "abstain_no_data" and _BROAD_REFUSAL.search(a[:200]) is not None


def _finish(r, refused):
    r["refused_n"] = refused
    if r.get("grading_mode") == "abstain_no_data":
        # Bịa số liệu = KHÔNG từ chối mà vẫn nêu con số (số trích lại từ ngữ cảnh khi đang từ chối không tính)
        r["abstain_violation"] = (not refused) and len(extract_numbers(r.get("answer") or "")) > 0
    return r


def norm_tea(r):
    r = dict(r)
    return _finish(r, _refused(r) or not r.get("gate_relevant", True))


def norm_van(r):
    r = dict(r)
    return _finish(r, _refused(r))


def load_primary():
    tea = {r["id"]: norm_tea(r) for r in json.loads(Path(glob.glob(TEA_RUN_GLOB)[0]).read_text(encoding="utf-8"))["records"]}
    van = {r["id"]: norm_van(r) for r in json.loads(OUT_PATH.read_text(encoding="utf-8"))["records"] if r.get("answer") and not str(r["answer"]).startswith("[LỖI")}
    ids = [i for i in van if i in tea]
    return "gpt-oss-120b", "qwen3.8-27b", {i: tea[i] for i in ids}, {i: van[i] for i in ids}


def load_pair(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    tea, van = {}, {}
    for r in d["records"]:
        if str(r.get("answer", "")).startswith("[LỖI"):
            continue
        (tea if r["system"] == "tea" else van)[r["id"]] = norm_tea(r) if r["system"] == "tea" else norm_van(r)
    ids = [i for i in van if i in tea]
    short = lambda m: m.split("/")[-1]
    return short(d["generator"]), short(d["judge"]), {i: tea[i] for i in ids}, {i: van[i] for i in ids}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def f(v, d=2):
    return "—" if v is None else f"{v:.{d}f}"


def score(rec, key):
    """Điểm đầu-cuối: có chấm -> điểm thật; bị từ chối -> điểm thấp nhất; còn lại (lỗi chấm/chưa chấm) -> None."""
    if rec.get("judge"):
        v = rec["judge"].get(key)
        return v if isinstance(v, (int, float)) else None
    if rec["refused_n"]:
        return 1.0 if key == "correctness" else 0.0
    return None


def boot(a, b, rng):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a)
    if n < 3:
        return None
    d = [a[i].mean() - b[i].mean() for i in (rng.integers(0, n, n) for _ in range(N_BOOT))]
    return float((a - b).mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def analyze(gen, judge, tea, van, rng):
    ids = list(tea)
    sem = [i for i in ids if van[i]["grading_mode"] == "semantic_factual"]
    ab = [i for i in ids if van[i]["grading_mode"] == "abstain_no_data"]
    both = [i for i in sem if tea[i].get("judge") and van[i].get("judge")]
    e2e = [i for i in sem if score(tea[i], "correctness") is not None and score(van[i], "correctness") is not None]
    out = {"gen": gen, "judge": judge, "n_sem": len(sem), "n_ab": len(ab), "n_both": len(both), "n_e2e": len(e2e)}
    for name, recs in (("tea", tea), ("van", van)):
        out[f"{name}_cond"] = {k: mean([recs[i]["judge"].get(k) for i in both]) for k in ("correctness", "faithfulness", "key_point_coverage")}
        out[f"{name}_e2e"] = {k: mean([score(recs[i], k) for i in e2e]) for k in ("correctness", "key_point_coverage")}
        out[f"{name}_wrong_refuse"] = sum(recs[i]["refused_n"] for i in sem)
        out[f"{name}_unsup"] = sum(bool(recs[i].get("unsupported_numbers")) for i in sem)
        out[f"{name}_hit_src"] = sum(bool(recs[i].get("hit_source_chunk")) for i in sem) if name == "van" else None
        out[f"{name}_abst_ok"] = sum(recs[i]["refused_n"] for i in ab)
        out[f"{name}_abst_viol"] = sum(bool(recs[i].get("abstain_violation")) for i in ab)
        lat = [recs[i].get("latency_s") for i in sem if recs[i].get("latency_s")]
        out[f"{name}_lat"] = mean(lat)
    out["diff_cond"] = boot([tea[i]["judge"]["correctness"] for i in both], [van[i]["judge"]["correctness"] for i in both], rng) if both else None
    out["diff_e2e"] = boot([score(tea[i], "correctness") for i in e2e], [score(van[i], "correctness") for i in e2e], rng) if e2e else None
    return out


def human_sheet(tea, van, n=30):
    """Phiếu chấm tay: ẩn tên hệ thống, đảo ngẫu nhiên A/B; đáp án ẩn lưu ra file riêng."""
    rng = random.Random(SEED)
    rows_by_id = {r["id"]: r for r in build_sample()}
    ids = [i for i in tea if van[i]["grading_mode"] == "semantic_factual" and not tea[i]["refused_n"] and not van[i]["refused_n"]]
    rng.shuffle(ids)
    ids = ids[:n]
    key, out = {}, []
    for i in ids:
        r = rows_by_id[i]
        tea_is_a = rng.random() < 0.5
        a, b = (tea[i], van[i]) if tea_is_a else (van[i], tea[i])
        key[i] = {"A": "Tea AI" if tea_is_a else "RAG thường", "B": "RAG thường" if tea_is_a else "Tea AI"}
        kp = r.get("answer_key_points") or []
        if isinstance(kp, str):
            kp = json.loads(kp)
        out.append({"id": i, "câu hỏi": r["question"], "đáp án chuẩn": r["expected_answer"], "các ý chính": " | ".join(kp),
                    "trả lời A": a["answer"], "trả lời B": b["answer"],
                    "điểm A (1-5)": "", "điểm B (1-5)": "", "ghi chú": ""})
    with SHEET.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    KEY.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rng = np.random.default_rng(SEED)
    configs = [load_primary()]
    for p in sorted(glob.glob(str(RUNS / "pair_*__judge_*.json"))):
        configs.append(load_pair(p))
    res = [analyze(*c, rng) for c in configs]

    L = ["# So sánh Tea AI với RAG thường qua nhiều model sinh và model chấm\n",
         "Mỗi dòng là một cấu hình (model sinh / model chấm). Model chấm luôn khác họ với model sinh. Tea AI = hybrid + cổng + prompt ràng buộc; "
         "RAG thường = embedding đa ngữ dense top-3 + prompt chung. Cùng câu hỏi cho hai hệ thống trong từng cấu hình.\n"]
    L.append("## 1. Câu có đáp án chuẩn: điểm đầu-cuối (câu bị từ chối nhầm tính điểm thấp nhất)\n")
    L.append("| Model sinh / chấm | N cặp | Correctness Tea AI | Correctness RAG thường | Chênh lệch (KTC 95%) | Coverage Tea AI | Coverage RAG thường | Từ chối nhầm Tea AI | Từ chối nhầm RAG thường |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in res:
        d = r["diff_e2e"]
        L.append(f"| {r['gen']} / {r['judge']} | {r['n_e2e']} | {f(r['tea_e2e']['correctness'])} | {f(r['van_e2e']['correctness'])} | "
                 f"{('%+.2f [%+.2f, %+.2f]' % d) if d else '—'} | {f(r['tea_e2e']['key_point_coverage'], 3)} | {f(r['van_e2e']['key_point_coverage'], 3)} | "
                 f"{r['tea_wrong_refuse']}/{r['n_sem']} | {r['van_wrong_refuse']}/{r['n_sem']} |")
    L.append("\n## 2. Chỉ câu cả hai hệ thống đều được chấm (có điều kiện)\n")
    L.append("| Model sinh / chấm | N cặp | Correctness Tea AI / RAG thường | Faithfulness Tea AI / RAG thường | Coverage Tea AI / RAG thường | Chênh lệch correctness (KTC 95%) |")
    L.append("|---|---|---|---|---|---|")
    for r in res:
        d = r["diff_cond"]
        L.append(f"| {r['gen']} / {r['judge']} | {r['n_both']} | {f(r['tea_cond']['correctness'])} / {f(r['van_cond']['correctness'])} | "
                 f"{f(r['tea_cond']['faithfulness'], 3)} / {f(r['van_cond']['faithfulness'], 3)} | "
                 f"{f(r['tea_cond']['key_point_coverage'], 3)} / {f(r['van_cond']['key_point_coverage'], 3)} | {('%+.2f [%+.2f, %+.2f]' % d) if d else '—'} |")
    L.append("\n## 3. Câu thiếu dữ liệu (phải từ chối, không bịa số liệu) và số liệu không căn cứ\n")
    L.append("| Model sinh / chấm | N câu thiếu dữ liệu | Từ chối đúng Tea AI / RAG thường | Bịa số liệu Tea AI / RAG thường | Câu có số liệu không căn cứ Tea AI / RAG thường |")
    L.append("|---|---|---|---|---|")
    for r in res:
        L.append(f"| {r['gen']} / {r['judge']} | {r['n_ab']} | {r['tea_abst_ok']} / {r['van_abst_ok']} | {r['tea_abst_viol']} / {r['van_abst_viol']} | {r['tea_unsup']} / {r['van_unsup']} |")
    L.append("\n## 4. Độ trễ trung bình một câu (s, gồm truy xuất và sinh; đo khi Groq còn giới hạn tốc độ nên chỉ mang tính tham khảo)\n")
    L.append("| Model sinh | Tea AI | RAG thường |")
    L.append("|---|---|---|")
    for r in res:
        L.append(f"| {r['gen']} | {f(r['tea_lat'], 1)} | {f(r['van_lat'], 1)} |")

    # Phiếu chấm tay dùng cấu hình chính
    _, _, tea0, van0 = configs[0]
    n_sheet = human_sheet(tea0, van0)
    L.append(f"\n## 5. Kiểm chứng bằng người\n")
    L.append(f"Đã xuất phiếu chấm tay {n_sheet} cặp câu trả lời (ẩn tên hệ thống, đảo ngẫu nhiên vị trí A/B): `docs/phieu_cham_tay_cap_tra_loi.csv`. "
             "Người chấm điền điểm 1-5 cho A và B; đáp án ẩn nằm ở `docs/phieu_cham_tay_dap_an_an.json`. Sau khi có phiếu đã điền, chạy "
             "`python -m backend.evaluation.human_agreement` để tính mức đồng thuận giữa người và model chấm.")
    L.append("\n## Lưu ý\n")
    L.append("- Mỗi cấu hình dùng cỡ mẫu khác nhau (cấu hình chính lớn hơn) nên so sánh giữa các dòng chủ yếu nhìn hướng và độ lớn, không so từng con số.")
    L.append("- Model chấm khác họ với model sinh nhưng vẫn là LLM; chưa thay thế được người chấm.")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    (RUNS / "pair_report_raw.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
