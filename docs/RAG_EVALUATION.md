# Đánh giá và thiết kế RAG

Tài liệu này ghi lại cách RAG của Tea AI được đo, các quyết định thiết kế dựa trên số liệu, và những hạn chế còn lại.

Tái lập kết quả:

```bash
python -m rag.ingest                                  # lập chỉ mục (bắt buộc sau khi đổi cách tạo embedding)
python -m rag.evaluation.run_eval --report docs/RAG_EVAL_RESULTS.md
python -m pytest rag/tests -q                         # gồm test hồi quy chất lượng
```

## 1. Thiết kế truy xuất

```text
Câu hỏi
  │
  ├─► Embedding (bkai vietnamese-bi-encoder, 768 chiều, tách từ pyvi)  ─► cosine với mọi chunk
  │        (chunk được nhúng dưới dạng "tiêu đề + nội dung")
  │
  ├─► BM25 (từ đơn + bigram, tiêu đề tính 2 lần)                     ─► điểm BM25 với mọi chunk
  │
  ▼
Điểm hybrid = 0.7 × cosine + 0.3 × (BM25 / BM25 cao nhất)  ─►  Top-3
  │
  ▼
Cổng "có liên quan": cosine cao nhất ≥ 0.38 VÀ BM25 cao nhất ≥ 10
  │  không đạt  ─►  trả lời "chưa có đủ thông tin", không gọi LLM, không hiện nguồn
  ▼  đạt
Ngữ cảnh + nguồn ─► LLM (Groq) có ràng buộc chỉ trả lời dựa trên ngữ cảnh
```

Mã nguồn: `rag/retriever.py`, `rag/bm25.py`, `rag/text_utils.py`, `rag/vector_store.py`, cấu hình ở `rag/config.py`.

## 2. Bộ đánh giá

`rag/evaluation/eval_set.json` gồm 76 câu:

| Loại | Số câu | Kỳ vọng |
|---|---|---|
| `in_domain` | 64 | Top-k chứa ít nhất một chunk liên quan (người lập đã gán danh sách chunk liên quan cho từng câu) |
| `out_of_domain` | 8 | Bị từ chối (ví dụ "sửa xe máy", "giá Bitcoin") |
| `knowledge_gap` | 4 | Thuộc lĩnh vực chè nhưng cơ sở tri thức không có (ví dụ "lá chè bị vàng", "pha trà ô long") |

Chỉ số: Hit@k (có chunk đúng trong top-k), MRR, nDCG@3, Precision@3; với cổng từ chối là tỉ lệ nhận đúng và từ chối đúng.

## 3. Kết quả

Đo trên cùng bộ 64 câu trong phạm vi:

| Cấu hình | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 |
|---|---|---|---|---|---|
| Phase 6 cũ: cosine, chỉ nhúng nội dung | 0.531 | 0.750 | 0.797 | 0.639 | 0.507 |
| Cosine, nhúng tiêu đề + nội dung | 0.719 | 0.828 | 0.875 | 0.781 | 0.617 |
| BM25 (tiêu đề ×2) | 0.906 | 0.984 | 0.984 | 0.943 | 0.826 |
| Hybrid RRF | 0.844 | 0.969 | 0.984 | 0.908 | 0.757 |
| **Hybrid có trọng số (đang dùng)** | **0.922** | **0.984** | **1.000** | **0.956** | **0.826** |

Dòng "Phase 6 cũ" và dòng RRF được đo bằng mã thử nghiệm trong quá trình thiết kế (chỉ mục cũ đã được thay nên không còn tái lập bằng `run_eval`). Ba dòng còn lại tái lập được bằng `run_eval` với các chế độ `dense`, `bm25`, `hybrid` trên chỉ mục hiện tại. Kết quả chi tiết mới nhất nằm trong [RAG_EVAL_RESULTS.md](RAG_EVAL_RESULTS.md).

Cổng từ chối trước khi đổi sang bkai (xem mục 3b cho kết quả hiện tại), so với ngưỡng cosine 0.42 của Phase 6:

| Cổng | Nhận đúng câu trong phạm vi | Từ chối đúng câu ngoài phạm vi |
|---|---|---|
| Phase 6: cosine (chỉ nội dung) ≥ 0.42 | 96.9% | 41.7% |
| Hiện tại: cosine ≥ 0.30 và BM25 ≥ 10 | 100% | 58.3% |

### Các quyết định rút ra từ số liệu

1. **Nhúng cả tiêu đề cùng nội dung.** Tiêu đề chứa chủ đề của chunk; chỉ riêng thay đổi này nâng Hit@1 từ 0.53 lên 0.72.
2. **Thêm BM25.** Câu hỏi về bệnh/sâu hại chứa nhiều thuật ngữ chuyên môn ("thối búp", "nhện đỏ") mà khớp từ khóa xử lý tốt hơn embedding đa ngôn ngữ cỡ nhỏ.
3. **Kết hợp có trọng số thay vì RRF.** RRF chỉ dùng thứ hạng nên bỏ mất thông tin về mức độ chênh lệch điểm; trên bộ này bản có trọng số cao hơn 4.8 điểm MRR.
4. **Không thêm reranker, HyDE hay mở rộng câu hỏi.** Hit@3 đã là 0.984 và Hit@5 là 1.0, còn dư địa rất nhỏ so với chi phí (một model reranker hàng trăm MB chạy cho mỗi câu hỏi). Điểm yếu còn lại nằm ở cổng từ chối và dữ liệu, không phải xếp hạng.

### Cập nhật sau khi thêm nguồn ngoài (171 chunk, 84 câu hỏi)

Thêm 9 chunk (FAO EcoCrop, Tang 2020) và 8 câu hỏi tương ứng. Kết quả hybrid trên 72 câu trong phạm vi: Hit@1 = 0,903, Hit@3 = 0,986, Hit@5 = 1,000, MRR = 0,947; cổng từ chối vẫn nhận đúng 100% câu trong phạm vi. Bảng ở mục 3 là số đo trên 64 câu ban đầu và giữ nguyên để so sánh với cấu hình Phase 6; chi tiết mới nhất ở [RAG_EVAL_RESULTS.md](RAG_EVAL_RESULTS.md).

## 3b. Đổi sang model embedding tiếng Việt (bkai)

**Bối cảnh.** Sau khi thấy dự án RAG-pipeline-visualizer không có kỹ thuật nào đáng thêm (xem `RAG_AUDIT.md`), tôi thử thay model embedding vì đây là thành phần yếu nhất: MiniLM đa ngữ nhỏ cho điểm cosine của câu ngoài phạm vi (trung vị 0,43) gần với câu trong phạm vi hơn mong muốn. Bộ nhớ đệm Hugging Face trên máy đã có sẵn `bkai-foundation-models/vietnamese-bi-encoder` (Apache-2.0), nên không cần tải thêm.

Cùng bộ 72 câu trong phạm vi + 12 câu ngoài phạm vi, cùng BM25 và trọng số 0,7/0,3:

| Cấu hình | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Cosine top-1 câu ngoài phạm vi (trung vị / lớn nhất) |
|---|---|---|---|---|---|---|
| MiniLM, chỉ vector | 0.681 | 0.778 | 0.833 | 0.739 | 0.590 | 0,43 / 0,77 |
| MiniLM + BM25 (trước đây) | 0.903 | 0.986 | 1.000 | 0.947 | 0.827 | 0,43 / 0,77 |
| bkai, chỉ vector | 0.847 | 0.931 | 0.958 | 0.891 | 0.782 | 0,24 / 0,47 |
| **bkai + BM25 (đang dùng)** | **0.917** | **0.986** | **1.000** | **0.953** | **0.866** | 0,24 / 0,47 |
| MiniLM + bkai + BM25 (thử, không dùng) | 0.958 | 1.000 | 1.000 | 0.979 | 0.890 | — |

**Cổng từ chối** (ngưỡng chọn trên nửa dữ liệu chẵn, kiểm tra trên nửa lẻ): bkai cosine ≥ 0,38 và BM25 ≥ 10 cho nhận đúng 100% và từ chối đúng 100% trên nửa kiểm tra (và trên toàn bộ tập); MiniLM chỉ đạt 94% và 83% trên nửa kiểm tra, và 67% từ chối đúng trên toàn bộ tập. Trên hệ thống thật, 5 câu trước đây lọt qua cổng ("sửa xe máy", "phở bò", "ghép cành sầu riêng", "pha trà ô long", "giá chè hôm nay") đều bị từ chối ngay trong khoảng 2 giây, không gọi LLM.

**Vì sao không dùng bản ghép hai model:** xếp hạng tốt hơn 3 câu (Hit@1 0,958) nhưng cổng từ chối kém hơn (đạt 92% từ chối đúng) và tốn thêm bộ nhớ, thời gian khởi động.

**Mức tin cậy.** Chỉ có 12 câu ngoài phạm vi, nên "100%" cần hiểu là "không có sai sót nào trên mẫu nhỏ này", không phải cam kết cho mọi câu hỏi thực tế. Khoảng cách giữa hai nhóm (0,24 so với 0,73 ở trung vị) đủ lớn để tin xu hướng, nhưng vẫn nên kiểm tra lại với bộ câu hỏi độc lập.

**Chi phí vận hành:** model 773 MB; backend khởi động khoảng 30 giây; cần `pyvi`. Đổi model bằng biến `RAG_EMBEDDING_MODEL` thì phải chạy lại `python -m rag.ingest` và hiệu chỉnh `RAG_MIN_COSINE`.

**Chưa đo được:** chất lượng câu chữ do LLM sinh ra (LLM có thể vẫn diễn giải thêm mục đích/nguyên nhân dù prompt đã cấm; xem ví dụ "đốn phớt chè để làm gì?"). Phần này cần một bộ đánh giá câu trả lời riêng (ví dụ người chấm hoặc LLM chấm độ bám nguồn).

## 3c. Độ bền trước cách gõ của người dùng (gõ không dấu, gõ nhầm)

Nông dân gõ trên điện thoại thường không gõ dấu tiếng Việt. Phép thử (`python -m rag.evaluation.robustness`) biến đổi cùng bộ câu hỏi rồi đo lại, gồm cả cổng từ chối. Kết quả đầy đủ: [RAG_ROBUSTNESS_RESULTS.md](RAG_ROBUSTNESS_RESULTS.md).

| Câu hỏi | Hit@3 hybrid trước khi sửa | Hit@3 hybrid sau khi sửa | Nhận đúng câu trong phạm vi (sau) | Từ chối đúng câu ngoài phạm vi (sau) |
|---|---|---|---|---|
| Có dấu (gốc) | 0,986 | 0,986 | 100% | 100% |
| Không dấu | **0,361** | **0,944** | 94,4% | 75,0% |
| Không dấu + gõ nhầm | 0,222 | 0,931 | 70,8% | 100% |
| Có dấu + gõ nhầm | 0,986 | 0,986 | 88,9% | 100% |

**Vấn đề phát hiện:** tách từ BM25 và embedding đều nhạy với dấu, nên câu không dấu gần như không tìm đúng tài liệu (Hit@3 0,36). Khôi phục dấu bằng `pyvi` không dùng được (0/72 câu đúng hoàn toàn: "Bệnh thối búp" thành "Bẻnh thời bụp").

**Cách khắc phục đã áp dụng:**

1. **BM25 bỏ dấu** (cả tài liệu lẫn câu hỏi). Từ dừng được loại theo dạng có dấu trước khi bỏ dấu, nếu không "cỏ" bị xóa nhầm vì trùng "có". Hit@3 của BM25 cho câu không dấu tăng từ 0,29 lên 0,99 và câu có dấu không bị giảm.
2. **Chỉ mục vector thứ hai cho văn bản đã bỏ dấu**, dùng khi câu hỏi hoàn toàn không có dấu. Hit@3 phần vector tăng từ 0,39 lên 0,82.
3. **Cổng từ chối riêng cho câu không dấu** (cosine trên chỉ mục bỏ dấu có thang điểm khác). Trước đó cổng chỉ nhận 5,6% câu không dấu trong phạm vi vì cosine sụp khi mất dấu; đây là lỗi sẽ xảy ra ngay khi đưa vào sử dụng nếu chỉ sửa xếp hạng.
4. Cổng câu có dấu bổ sung điều kiện "cosine ≥ 0,55 thì chấp nhận không cần BM25" (câu chung chung như "Sâu hại chính trên cây chè" có cosine cao nhưng ít từ khóa).

**Đánh đổi của cổng không dấu:** ngưỡng chọn nghiêng về không từ chối nhầm (nhận đúng 94%, từ chối đúng 75%); nâng ngưỡng thì từ chối đúng 100% nhưng nhận đúng chỉ 86%. Chỉ có 12 câu ngoài phạm vi nên các tỉ lệ này thô.

**Còn yếu:** câu vừa không dấu vừa gõ nhầm (nhận đúng 71%), và câu gõ dấu không đầy đủ (một phần có dấu, một phần không) bị coi là có dấu nên dùng cosine thang có dấu.

## 4. Hạn chế cần nêu khi bảo vệ

- **Bộ đánh giá nhỏ và do một người lập.** 64 câu, nhãn liên quan gán theo nội dung chunk. Nhiều câu dùng từ gần với tiêu đề chunk nên có lợi cho BM25, có thể làm số đo lạc quan hơn thực tế. Nên nhờ người khác viết thêm 30–50 câu hỏi độc lập (chưa nhìn tiêu đề chunk) làm tập kiểm tra.
- **Tham số chọn trên chính bộ này** (trọng số 0.7, ngưỡng 0.30 và 10), chưa có tập kiểm tra độc lập, nên các số trong mục 3 có thể lạc quan. Các ngưỡng được chọn ở vùng "nhận đủ 100% câu trong phạm vi" để tránh từ chối nhầm người dùng thật, đổi lại cổng lọc ngoài phạm vi kém chặt.
- **Cổng từ chối chưa lọc hết câu ngoài phạm vi.** 5/12 câu lọt qua ("sửa xe máy", "phở bò", "ghép cành sầu riêng", "pha trà ô long", "giá chè hôm nay"), vì chúng có từ trùng với chunk kỹ thuật (ví dụ "máy", "cành", "chè"). Lớp phòng thủ thứ hai là prompt ràng buộc của LLM (`backend/services/llm_service.py`), chưa được kiểm tra tự động vì cần gọi Groq thật.
- **Cơ sở tri thức có khoảng trống nội dung**: không có chunk về lá vàng/thiếu dinh dưỡng, giá cả, pha chế. Cách khắc phục là bổ sung tài liệu nguồn thật, không phải chỉnh ngưỡng.
- **Metadata `category` gán sai ở nhiều chunk.** Ví dụ `tea_000004` "Thiết kế hàng chè và đào hố" mang nhãn `pest_and_disease`; ước lượng theo tiêu đề có ít nhất 23 chunk thuộc nhóm này không liên quan tới sâu bệnh. Vì vậy chưa nên dùng bộ lọc `category` trong truy xuất cho tới khi gán nhãn lại (thuộc Phase 4).

## 5. Vận hành

- Chỉ mục có phiên bản (`INDEX_VERSION` trong `rag/config.py`). Nếu chỉ mục cũ hoặc chưa tạo, API trả HTTP 503 kèm hướng dẫn chạy `python -m rag.ingest`.
- Retriever nạp một lần lúc server khởi động (`backend/main.py`), mọi request dùng chung.
- Ngưỡng có thể ghi đè bằng biến môi trường `RAG_MIN_COSINE`, `RAG_MIN_BM25`.
