# Kết quả đánh giá Retrieval trên bộ 1000 câu hỏi

Nguồn: `E:\NHÁP 2\tea_chatbot_qa_test_1000.jsonl`. Tổng 1000 câu, trong đó **928 câu thuộc phạm vi RAG** được đánh giá ở đây (loại 72 câu `Tea_Regions_Project_Config` vì nguồn này không được ingest vào ChromaDB, không đi qua RAG retriever).

Ngưỡng Context Recall (xấp xỉ, dựa cosine, KHÔNG phải LLM chấm attribution như RAGAS gốc): cosine ≥ 0.5 giữa key point và top-3 chunk truy xuất.


## Tổng thể

| N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall (xấp xỉ) |
|---|---|---|---|---|---|---|
| 928 | 0.929 | 0.991 | 1.000 | 0.957 | 0.964 | 0.661 |

## Theo question_type

| question_type | N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall |
|---|---|---|---|---|---|---|---|
| completeness | 171 | 0.971 | 0.994 | 1.000 | 0.983 | 0.985 | 0.662 |
| direct_grounded | 171 | 0.994 | 1.000 | 1.000 | 0.996 | 0.997 | 0.668 |
| domain_question | 171 | 0.971 | 1.000 | 1.000 | 0.985 | 0.989 | 0.667 |
| numeric_extraction | 73 | 0.986 | 1.000 | 1.000 | 0.993 | 0.995 | 0.699 |
| paraphrase | 171 | 0.988 | 1.000 | 1.000 | 0.993 | 0.995 | 0.669 |
| source_constrained | 171 | 0.696 | 0.959 | 1.000 | 0.810 | 0.841 | 0.625 |

## Theo difficulty

| difficulty | N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall |
|---|---|---|---|---|---|---|---|
| easy | 342 | 0.991 | 1.000 | 1.000 | 0.995 | 0.996 | 0.668 |
| medium | 513 | 0.879 | 0.984 | 1.000 | 0.926 | 0.938 | 0.652 |
| hard | 73 | 0.986 | 1.000 | 1.000 | 0.993 | 0.995 | 0.699 |

## Theo nguồn (dataset)

| dataset | N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall |
|---|---|---|---|---|---|---|---|
| FAO_EcoCrop_Camellia_sinensis | 36 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.884 |
| LaiChau_Tea_Technical_Guideline | 255 | 0.847 | 0.980 | 1.000 | 0.903 | 0.919 | 0.689 |
| TL1_Tea_Technical_Guideline | 505 | 0.947 | 0.994 | 1.000 | 0.969 | 0.975 | 0.621 |
| Tang2020_Tea_Nutrient_QUEFTS | 18 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.722 |
| TeaLeafDiseaseBD | 114 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.699 |
