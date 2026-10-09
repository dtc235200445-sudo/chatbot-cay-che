from backend.evaluation.answer_eval import (
    copy_ratio,
    extract_numbers,
    faithfulness,
    is_refusal,
    normalize_number,
    parse_judge_json,
    select_questions,
    summarize,
    unsupported_numbers,
)
from backend.services.assistant_service import NO_KNOWLEDGE_ANSWER


def test_normalize_number_ignores_separators():
    assert normalize_number("1.800") == normalize_number("1800") == "1800"
    assert normalize_number("10,1") == normalize_number("10.1") == "101"


def test_extract_numbers_skips_chunk_ids_source_tags_and_list_markers():
    text = "1. Nhiệt độ 18–28°C [tea_000053].\n2. Nguồn 1 nói mưa 1.700 mm (Nguồn 3)."
    assert extract_numbers(text) == ["18", "28", "1700"]


def test_thousands_separated_by_space_is_one_number():
    assert extract_numbers("mật độ 20 000 – 22 000 cây/ha") == ["20000", "22000"]
    assert unsupported_numbers("16 000 cây/ha", "mật độ 16.000 cây/ha", "Mật độ?") == []
    # Năm đứng cạnh một số khác không được ghép nhầm
    assert extract_numbers("năm 2025 và 100 cây") == ["2025", "100"]


def test_extract_numbers_handles_narrow_no_break_space():
    assert extract_numbers("45 – 60 kg") == ["45", "60"]


def test_unsupported_numbers_flags_invented_figures():
    context = "Cây chè sinh trưởng tốt ở nhiệt độ 18 - 28°C; lượng mưa trung bình 1.700 mm."
    assert unsupported_numbers("Nhiệt độ 18–28°C, mưa 1.700 mm.", context, "Nhiệt độ nào?") == []
    assert unsupported_numbers("Nhiệt độ 18–28°C, năng suất 35 tấn/ha.", context, "Nhiệt độ nào?") == ["35"]


def test_numbers_in_question_are_allowed():
    assert unsupported_numbers("Với năng suất 60 tạ/ha cần bón thêm.", "Bón phân theo tuổi cây.", "Chè 60 tạ/ha bón gì?") == []


def test_is_refusal():
    assert is_refusal(NO_KNOWLEDGE_ANSWER)
    assert is_refusal("Hiện tại cơ sở tri thức chưa có đủ thông tin để trả lời chính xác câu hỏi này của bạn.")
    long_partial = "Bệnh thối búp gây hại ở lá non. " * 10 + "Tuy nhiên cơ sở tri thức chưa có đủ thông tin về liều thuốc."
    assert not is_refusal(long_partial)


def test_parse_judge_json_variants():
    good = '{"claims": [{"claim": "a", "supported": true}], "relevance": 5, "completeness": 4, "comment": "ok"}'
    assert parse_judge_json(good)["relevance"] == 5
    assert parse_judge_json(f"```json\n{good}\n```")["completeness"] == 4
    assert parse_judge_json(f"<think>suy nghĩ {{lung tung}}</think>\n{good}")["comment"] == "ok"
    assert parse_judge_json("không phải json") is None
    assert parse_judge_json('{"relevance": 3}') is None  # thiếu claims


def test_faithfulness():
    assert faithfulness([]) is None
    assert faithfulness([{"supported": True}, {"supported": False}, {"supported": True}, {"supported": True}]) == 0.75
    assert faithfulness([{"supported": "true"}]) == 0.0  # chỉ chấp nhận đúng kiểu boolean


def test_summarize_counts_and_means():
    records = [
        {"type": "in_domain", "refused": False, "gate_relevant": True, "unsupported_numbers": ["9"], "latency_s": 2.0, "judge_error": None,
         "judge": {"faithfulness": 1.0, "relevance": 5, "completeness": 4}},
        {"type": "in_domain", "refused": True, "gate_relevant": True, "unsupported_numbers": [], "latency_s": 1.0, "judge_error": None, "judge": None},
        {"type": "out_of_domain", "refused": False, "gate_relevant": True, "unsupported_numbers": [], "latency_s": 2.0, "judge_error": None, "judge": None},
        {"type": "knowledge_gap", "refused": True, "gate_relevant": False, "unsupported_numbers": [], "latency_s": 1.0, "judge_error": None, "judge": None},
    ]
    s = summarize(records)
    assert (s["n_in_domain"], s["n_out_of_scope"]) == (2, 2)
    assert s["wrongly_refused"] == 1 and s["wrongly_answered"] == 1
    assert s["answers_with_unsupported_numbers"] == 1
    assert s["faithfulness"] == 1.0 and s["relevance"] == 5 and s["completeness"] == 4


def test_select_questions_is_deterministic_and_includes_all_out_of_scope():
    a, b = select_questions(10), select_questions(10)
    assert [q["id"] for q in a] == [q["id"] for q in b]
    assert sum(1 for q in a if q["type"] == "in_domain") == 10
    assert sum(1 for q in a if q["type"] != "in_domain") == 12


def test_copy_ratio_detects_verbatim_copying():
    context = "Bệnh thường gây hại ở lá non, cuống lá và cành non; vết bệnh lúc đầu bằng đầu kim có màu nâu đen."
    verbatim = "Bệnh thường gây hại ở lá non, cuống lá và cành non; vết bệnh lúc đầu bằng đầu kim có màu nâu đen."
    paraphrase = "Nấm tấn công phần non của cây, khởi đầu là những đốm rất nhỏ sẫm màu."
    assert copy_ratio(verbatim, context) == 1.0
    assert copy_ratio(paraphrase, context) == 0.0
    assert copy_ratio("quá ngắn", context) is None
