# Phase 0 — Đề tài và phạm vi

> **Ghi chú về tài liệu:** Phase 0–2 được viết bổ sung sau khi hệ thống đã hoàn thành Phase 3–10, nhằm chính thức hóa phạm vi, yêu cầu và kiến trúc. Nội dung mô tả hệ thống **như đã xây dựng**, đối chiếu với mã nguồn và kết quả kiểm thử; không dựa trên khảo sát người dùng thực tế (chưa thực hiện).

## 1. Đề tài

**Tea Scholar AI — Trợ lý tri thức và hỏi đáp về cây chè Việt Nam.**

Hệ thống cho phép người dùng đặt câu hỏi bằng tiếng Việt về kỹ thuật trồng, chăm sóc, sâu bệnh hại, thu hoạch, chế biến chè và thời tiết các vùng chè. Câu trả lời được sinh bởi mô hình ngôn ngữ nhưng **chỉ dựa trên cơ sở tri thức đã kiểm soát và dữ liệu thời tiết trực tiếp**, kèm trích dẫn nguồn, để hạn chế việc mô hình tự bịa thông tin.

## 2. Bối cảnh và vấn đề

Tri thức kỹ thuật về chè nằm rải rác trong các tài liệu hướng dẫn dạng PDF/văn bản dài, khó tra cứu nhanh theo tình huống ("lá chè có chấm xám phải làm gì?"). Mô hình ngôn ngữ đa dụng trả lời trôi chảy nhưng có thể đưa ra hướng dẫn kỹ thuật không có căn cứ, điều nguy hiểm trong nông nghiệp (ví dụ sai loại thuốc, sai liều). Vấn đề cần giải quyết:

1. Tra cứu nhanh tri thức chè bằng ngôn ngữ tự nhiên.
2. Câu trả lời phải **có nguồn, kiểm chứng được**, và hệ thống phải **biết từ chối** khi cơ sở tri thức không có thông tin.
3. Kết hợp điều kiện thời tiết hiện tại vào tư vấn (ví dụ độ ẩm cao thuận lợi cho bệnh thối búp).

## 3. Mục tiêu

| # | Mục tiêu | Cách kiểm chứng |
|---|---|---|
| G1 | Xây dựng cơ sở tri thức có cấu trúc từ các tài liệu kỹ thuật chè | 171 chunk (162 gốc + 9 từ nguồn ngoài), có metadata nguồn; kiểm tra bằng `validate_knowledge_base.py` và `database/verify_database.py` |
| G2 | Truy xuất đúng đoạn tri thức liên quan tới câu hỏi | Hit@3 = 0.98, MRR = 0.96 trên bộ 64 câu (`docs/RAG_EVALUATION.md`) |
| G3 | Trả lời có trích dẫn nguồn và từ chối khi thiếu tri thức | Test `test_assistant*.py`, cổng từ chối trong `rag/retriever.py` |
| G4 | Cung cấp thời tiết thời gian thực cho vùng trồng chè và kết hợp vào câu trả lời | Tích hợp Open-Meteo, test `test_weather_integration.py` |
| G5 | Có hệ thống tài khoản và lưu lịch sử hội thoại | JWT, bảng `chat_sessions`/`chat_messages`, test phân quyền |
| G6 | Có giao diện web dễ dùng | Frontend React, các trang trợ lý, tra cứu, thời tiết |

## 4. Đối tượng sử dụng

| Nhóm | Nhu cầu chính |
|---|---|
| Nông hộ, hợp tác xã trồng chè | Hỏi nhanh cách phòng trừ sâu bệnh, bón phân, đốn hái |
| Cán bộ khuyến nông, kỹ thuật viên | Tra cứu hướng dẫn kỹ thuật kèm nguồn |
| Sinh viên, nhà nghiên cứu | Tra cứu tri thức và xem nguồn trích dẫn |
| Quản trị viên | Quản lý dữ liệu tri thức (hiện thực hiện qua script, chưa có giao diện quản trị) |

## 5. Phạm vi

### Trong phạm vi

- Hỏi đáp tiếng Việt về chè dựa trên cơ sở tri thức (RAG) và LLM.
- Truy xuất hybrid (embedding + BM25) có cổng từ chối câu hỏi ngoài cơ sở tri thức.
- Thời tiết hiện tại cho 12 vùng chè (Phú Thọ, Thái Nguyên, Lâm Đồng, Bảo Lộc, Đà Lạt, Lai Châu, Sơn La, Mộc Châu, Hà Giang, Yên Bái, Tuyên Quang, Nghệ An).
- Câu hỏi kết hợp tri thức và thời tiết; hội thoại nhiều lượt trong một phiên.
- Đăng ký, đăng nhập, phiên chat gắn với người dùng.
- Tra cứu từ khóa trong cơ sở tri thức; API đọc dữ liệu bệnh hại, chủ đề canh tác, tài liệu nguồn.
- REST API có tài liệu OpenAPI (`/docs`); giao diện web.

### Ngoài phạm vi (không thực hiện trong đồ án này)

| Hạng mục | Ghi chú |
|---|---|
| Chẩn đoán bệnh qua ảnh lá chè | Giao diện có nút nhưng đã vô hiệu hóa và ghi rõ "đang phát triển". Bộ dữ liệu TeaLeafDiseaseBD chỉ được dùng như tài liệu mô tả, không huấn luyện mô hình thị giác |
| Dự báo thời tiết nhiều ngày | Chỉ có thời tiết hiện tại |
| Khuyến cáo liều lượng thuốc cụ thể vượt ngoài văn bản nguồn | Hệ thống chỉ trích dẫn nguồn, không thay thế tư vấn chuyên gia |
| Giao diện quản trị nội dung tri thức | Cập nhật tri thức qua script (`scripts/build_knowledge_base.py`, `database/seed.py`, `rag/ingest.py`) |
| Ứng dụng di động gốc, đa ngôn ngữ ngoài tiếng Việt | Giao diện web responsive, tiếng Việt |
| Học từ phản hồi người dùng, fine-tune mô hình | Không thực hiện |

## 6. Nguồn tri thức

| Mã | Tài liệu | Số chunk |
|---|---|---|
| TL1 | Tài liệu kỹ thuật trồng và chăm sóc chè (một số chunk trích dẫn quy trình chuẩn TL2 và các nghiên cứu thích ứng biến đổi khí hậu) | 95 |
| LaiChau | Quyết định 450/QĐ-SNNMT Lai Châu 2025, hướng dẫn kỹ thuật trồng và chăm sóc chè | 45 |
| TeaLeafDiseaseBD | Tài liệu mô tả bộ dữ liệu ảnh lá chè bệnh (Bangladesh, 2025) | 22 |
| FAO EcoCrop | Yêu cầu sinh thái của chè (CC BY 4.0) | 6 |
| Tang và cộng sự (2020) | Nhu cầu N, P, K của chè theo vụ, Scientific Reports (CC BY 4.0) | 3 |

Chi tiết giấy phép và các nguồn đã xem xét: [DATA_SOURCES.md](DATA_SOURCES.md).

Lưu ý: 22 chunk của TeaLeafDiseaseBD mô tả bộ dữ liệu (thiết bị chụp, định dạng nhãn YOLO...) hơn là kiến thức canh tác, và các bệnh trong đó thuộc bối cảnh Bangladesh. Chúng phục vụ hướng chẩn đoán ảnh trong tương lai và có thể gây nhiễu khi truy xuất; nên cân nhắc tách khỏi tập tri thức hỏi đáp (xem `docs/RAG_EVALUATION.md`, mục Hạn chế).

## 7. Giả định và ràng buộc

- Người dùng có kết nối Internet (gọi Groq và Open-Meteo).
- Dịch vụ LLM là Groq (mô hình mặc định `openai/gpt-oss-120b`; model có thể bị nhà cung cấp ngừng, xem `.env.example`), cần khóa API; giới hạn tần suất của Groq ảnh hưởng độ khả dụng.
- Dữ liệu tri thức là văn bản tiếng Việt đã được chia đoạn thủ công/bán tự động; chất lượng câu trả lời bị giới hạn bởi độ phủ của dữ liệu.
- Chạy trên máy phát triển với SQLite; PostgreSQL có thể cấu hình qua `DATABASE_URL` nhưng chưa được kiểm thử.
- Đồ án học thuật: không cam kết SLA hay tuân thủ quy định vận hành thương mại.

## 8. Rủi ro chính

| Rủi ro | Mức | Biện pháp đã áp dụng | Còn lại |
|---|---|---|---|
| LLM bịa thông tin | Cao | Prompt ràng buộc ngữ cảnh; cổng từ chối trước khi gọi LLM; hiển thị nguồn | Cổng chưa lọc hết câu ngoài phạm vi (58% từ chối đúng), chưa kiểm tra tự động câu trả lời LLM |
| Cơ sở tri thức thiếu chủ đề (ví dụ lá vàng, giá cả) | Trung bình | Từ chối rõ ràng, thông báo "chưa có đủ thông tin" | Cần bổ sung tài liệu nguồn thật |
| Phụ thuộc dịch vụ bên ngoài (Groq, Open-Meteo) | Trung bình | Mã lỗi rõ (502/503/504), thông báo thân thiện trên giao diện | Chưa có nhà cung cấp dự phòng |
| Lộ dữ liệu hội thoại | Trung bình | Kiểm tra chủ sở hữu phiên; người chưa đăng nhập không liệt kê được phiên | Phiên ẩn danh ai biết ID đều truy cập được khi gọi `/query` (giới hạn MVP đã ghi nhận) |
| Sai lệch dữ liệu (nhãn `category` sai ở ít nhất 23 chunk) | Thấp | Truy xuất không dùng bộ lọc `category` | Cần gán nhãn lại (Phase 4) |

## 9. Lộ trình

| Phase | Nội dung | Trạng thái |
|---|---|---|
| 0 | Chốt đề tài và phạm vi (tài liệu này) | Hoàn thành |
| 1 | Phân tích yêu cầu | Hoàn thành (`01_REQUIREMENTS.md`) |
| 2 | Thiết kế kiến trúc | Hoàn thành (`02_ARCHITECTURE.md`) |
| 3 | Thiết kế database | Hoàn thành (`DATABASE_SCHEMA.md`) |
| 4 | Xây dựng knowledge base | Hoàn thành, còn việc gán nhãn lại `category` và bổ sung nội dung |
| 5 | Backend/API | Hoàn thành |
| 6 | RAG | Hoàn thành, đã nâng cấp hybrid (`RAG_EVALUATION.md`) |
| 7 | Chatbot | Hoàn thành |
| 8 | Weather | Hoàn thành (thời tiết hiện tại) |
| 9 | AI Assistant (điều phối) | Hoàn thành |
| 10 | Frontend | Hoàn thành; giao diện được thiết kế lại ở Đợt 4 (lịch sử hội thoại, thời tiết đối chiếu ngưỡng); trang Cài đặt vẫn chỉ lưu cục bộ |
| 11+ | Hướng phát triển: chẩn đoán ảnh, dự báo nhiều ngày, pgvector, bộ đánh giá độc lập | Chưa thực hiện |
