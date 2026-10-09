# Độ bền của truy xuất trước cách gõ của người dùng

Cùng bộ câu hỏi đánh giá, biến đổi cách viết rồi đo lại. `Hit@3 hybrid` là chỉ số chính; hai cột cuối là cổng từ chối.

| Biến thể câu hỏi | Hit@1 hybrid | Hit@3 hybrid | MRR hybrid | Hit@3 chỉ vector | Hit@3 chỉ BM25 | Nhận đúng câu trong phạm vi | Từ chối đúng câu ngoài phạm vi |
|---|---|---|---|---|---|---|---|
| gốc (có dấu) | 0.917 | 0.986 | 0.950 | 0.931 | 0.986 | 100.0% | 100.0% |
| viết thường, bỏ dấu câu | 0.931 | 0.986 | 0.957 | 0.958 | 0.986 | 100.0% | 100.0% |
| có dấu + gõ nhầm | 0.889 | 0.986 | 0.935 | 0.903 | 0.931 | 88.9% | 100.0% |
| không dấu | 0.889 | 0.944 | 0.924 | 0.819 | 0.986 | 94.4% | 75.0% |
| không dấu + gõ nhầm | 0.792 | 0.931 | 0.869 | 0.681 | 0.931 | 70.8% | 100.0% |
