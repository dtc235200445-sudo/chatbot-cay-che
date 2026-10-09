# KNOWLEDGE BASE AUDIT & STANDARDIZATION REPORT

## 1. Sources Overview

Knowledge Base của dự án **Tea Scholar AI** được chuẩn hóa và hợp nhất từ 3 nguồn dữ liệu tài liệu chính thống:

* **Source 1:** `Tài liệu kỹ thuật trồng và chăm sóc chè (TL1)`
  * Số lượng: 95 chunks
  * Loại hình: Tài liệu kỹ thuật chuyên ngành nông nghiệp
  * Phạm vi: Kỹ thuật chọn đất, thiết kế đồi chè, bón phân, làm cỏ, đốn chè, tạo tán, giống chè, thời vụ thu hoạch.
* **Source 2:** `TeaLeafDiseaseBD: Annotated smartphone images and lesion-level labels of tea leaf diseases from Bangladesh`
  * Số lượng: 22 chunks
  * Loại hình: Tài liệu bộ dữ liệu hình ảnh sâu bệnh hại lá chè (Dataset Documentation)
  * Phạm vi: Thông số bộ dữ liệu 13.085 ảnh, thiết bị thu thập, phân loại 6 lớp bệnh hại trên lá chè (Red Spider, Brown Blight, Gray Blight, Helopeltis, Algal Leaf Spot, Red Rust).
* **Source 3:** `Quyết định 450/QĐ-SNNMT Lai Châu 2025` (`450-qd-ban-hanh-huong-dan-trong-cheban-hanh-24.7(1).pdf`)
  * Số lượng: 45 chunks
  * Loại hình: Tài liệu hướng dẫn kỹ thuật chính thức cấp Tỉnh / Cơ quan Nhà nước
  * Phạm vi: Căn cứ pháp lý, điều kiện sinh thái tỉnh Lai Châu, kỹ thuật trồng chè Shan, quản lý dịch hại tổng hợp (IPM), đốn và thu hoạch chè.

---

## 2. Chunk Statistics

* **Tổng số chunks (Total):** 162 chunks
* **Ký tự nhỏ nhất (Minimum):** 104 ký tự
* **Ký tự lớn nhất (Maximum):** 1.276 ký tự
* **Độ dài trung bình (Average):** 450.8 ký tự (~90-100 từ)
* **Độ dài trung vị (Median):** 382.5 ký tự

---

## 3. Category Statistics

Phân bố Chunks theo Phân loại danh mục (`category`):

* `cultivation_technique`: 40 chunks
* `pest_and_disease`: 40 chunks
* `fertilization`: 9 chunks
* `ecological_conditions`: 9 chunks
* `general_knowledge`: 8 chunks
* `disease_class`: 7 chunks
* `planting_material`: 5 chunks
* `harvesting`: 5 chunks
* `pruning`: 4 chunks
* `pest_and_disease_management`: 4 chunks
* `data_collection`: 2 chunks
* `lesion_annotation`: 2 chunks
* `dataset_metadata`: 2 chunks
* `soil_preparation`: 2 chunks
* `planting_density`: 2 chunks
* `soil_management`: 2 chunks
* Các hạng mục chuyên biệt khác (`dataset_overview`, `legal_basis`, `soil_conditions`, `planting_design`, `weed_management`, ...): 1 chunk cho mỗi danh mục.

---

## 4. Disease Statistics

Phân bố Chunks theo Nhãn Bệnh hại (`disease`):

* `None` (Không thuộc nội dung chuyên biệt về 1 loại bệnh cụ thể): 147 chunks
* `bọ trĩ`: 2 chunks
* `nhện đỏ`: 2 chunks
* `bệnh thối búp`: 1 chunk
* `bệnh chấm xám`: 1 chunk
* `bệnh đốm nâu`: 1 chunk
* `nhện đỏ, bọ xít muỗi`: 1 chunk
* `Red Spider`: 1 chunk
* `Brown Blight`: 1 chunk
* `Gray Blight`: 1 chunk
* `Helopeltis`: 1 chunk
* `Algal Leaf Spot`: 1 chunk
* `Red Rust`: 1 chunk
* `Healthy`: 1 chunk

---

## 5. Source Statistics

* **Tài liệu kỹ thuật trồng và chăm sóc chè (TL1):** 95 chunks (58.6%)
* **Quyết định 450/QĐ-SNNMT Lai Châu 2025:** 45 chunks (27.8%)
* **TeaLeafDiseaseBD Dataset Documentation:** 22 chunks (13.6%)

---

## 6. Metadata Completeness

Độ đầy đủ của các trường thông tin metadata trong toàn bộ Knowledge Base:

| Trường metadata | Mức độ đầy đủ (%) | Số lượng hiện có | Ghi chú |
| :--- | :---: | :---: | :--- |
| `source` | **100.0%** | 162 / 162 | Nguồn tài liệu gốc xác định rõ |
| `title` | **100.0%** | 162 / 162 | Tiêu đề đoạn văn đầy đủ |
| `content` | **100.0%** | 162 / 162 | Nội dung văn bản tri thức tự nhiên |
| `language` | **100.0%** | 162 / 162 | Chuẩn hóa mã `vi` |
| `category` | **100.0%** | 162 / 162 | Phân loại danh mục mạch lạc |
| `section` | **99.4%** | 161 / 162 | Tiêu đề mục/chương trong tài liệu |
| `region` | **100.0%** | 162 / 162 | Khu vực canh tác (`Việt Nam`, `Lai Châu`, `Bangladesh`) |
| `disease` | **9.3%** | 15 / 162 | Ghi nhận chính xác các nhãn bệnh hại |
| `year` | **41.4%** | 67 / 162 | Năm ban hành/xuất bản (2025/2026) |
| `page` | **27.8%** | 45 / 162 | Trang tài liệu trong PDF Quyết định 450 |

---

## 7. Duplicate Report

* **Exact duplicates (Trùng lặp 100% nội dung):** **0**
* **Near duplicates (Trùng lặp gần giống > 85%):** **15 pairs**
  * *Phân tích:* Các câu trùng lặp gần giống xuất hiện trong bộ dữ liệu `TeaLeafDiseaseBD` (các chunk từ `tealeaf_0006` đến `tealeaf_0011`) do có cùng mẫu câu mô tả lớp dữ liệu ảnh lá chè. Tuy nhiên, mỗi chunk mô tả một đối tượng bệnh khác nhau (`Red Spider`, `Brown Blight`, `Gray Blight`, `Helopeltis`, `Algal Leaf Spot`, `Red Rust`). Theo nguyên tắc bảo tồn dữ liệu, **100% các chunk này được giữ lại nguyên vẹn và độc lập**.

---

## 8. Validation Status

Đã khởi chạy kịch bản kiểm tra tự động `validate_knowledge_base.py`:

```text
========================================
KNOWLEDGE BASE VALIDATION
========================================
Total chunks: 162
Unique IDs: 162
Duplicate IDs: 0
Empty content: 0
Missing title: 0
Missing source: 0
Invalid JSON records: 0
Schema violations: 0
Exact duplicate content: 0
----------------------------------------
STATUS: PASS
========================================
```

---

## 9. Known Limitations

1. Nguồn `chunks.json` (TL1, 95 chunks) gốc không ghi kèm số trang PDF cụ thể nên trường `metadata.page` được thiết lập là `null` theo đúng nguyên tắc không tự bịa dữ liệu.
2. Các chunk thuộc loại tri thức chung (như chọn đất, làm cỏ, đốn chè) không gắn với tên bệnh cụ thể nên trường `disease` để trống `""`.
3. Toàn bộ 162 chunks đã được chuẩn hóa định dạng, cấp ID duy nhất (`tea_000001` đến `tea_000162`), sẵn sàng 100% để nạp vào Vector Database cho Phase 6 RAG.
