"""Tạo báo cáo Word: đánh giá Tea AI 3 tầng (quy trình + bảng kết quả)."""
import re
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = r"E:\CHATBOT CÂY CHÈ\docs\BAO_CAO_DANH_GIA_TEA_AI_3_TANG.docx"
GREEN = RGBColor(0, 0, 0)  # toàn bộ chữ màu đen
GREY = RGBColor(0, 0, 0)
FONT = "Times New Roman"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = sec.bottom_margin = Cm(2)

st = doc.styles["Normal"]
st.font.name, st.font.size = FONT, Pt(12.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.line_spacing = 1.2
for name, size in (("Heading 1", 15), ("Heading 2", 13.5), ("Heading 3", 12.5)):
    h = doc.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.color.rgb = FONT, Pt(size), True, GREEN
    h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    h.element.rPr.rFonts.set(qn("w:ascii"), FONT)
    h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        h.element.rPr.rFonts.attrib.pop(qn(attr), None)
    h.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True
for name in ("List Bullet", "List Number"):
    doc.styles[name].font.name = FONT
    doc.styles[name].font.size = Pt(12.5)


def para(text="", bold=False, italic=False, size=None, color=None, align=None, after=None):
    p = doc.add_paragraph()
    add_runs(p, text, bold, italic, size, color)
    if align:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def add_runs(p, text, bold=False, italic=False, size=None, color=None):
    """**đậm** trong chuỗi được in đậm."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        r = p.add_run(part)
        r.bold = bold or (i % 2 == 1)
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color


def bullet(text, style="List Bullet"):
    p = doc.add_paragraph(style=style)
    add_runs(p, text)
    p.paragraph_format.space_after = Pt(3)
    return p


_step = [0]


def steps_reset():
    _step[0] = 0


def step(text):
    _step[0] += 1
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.space_after = Pt(3)
    add_runs(p, f"Bước {_step[0]}. ", bold=True, color=GREEN)
    add_runs(p, text)
    return p


def note(text):
    return para(text, italic=True, size=11, color=GREY)


def shade(cell, hex_color):
    return  # không tô màu nền
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def table(header, rows, widths, highlight_col=None, font=11):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        add_runs(c.paragraphs[0], h, bold=True, size=font, color=RGBColor(0, 0, 0))
        shade(c, "1F5C3A")
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], str(v), size=font)
            if i > 0 and re.match(r"^(\*\*)?[+\-]?\d|^(Có|Không|Chưa có)", str(v)):
                cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if highlight_col is not None and i == highlight_col:
                shade(cells[i], "E6F2EA")
            elif ri % 2 == 1:
                shade(cells[i], "F5F5F5")
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.05
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ======================================================================= trang bìa
para("BÁO CÁO ĐÁNH GIÁ HỆ THỐNG", bold=True, size=20, color=GREEN, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para("Chatbot hỏi đáp cây chè Tea AI", bold=True, size=16, color=GREEN, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
para("Đánh giá 3 tầng: tìm tài liệu, câu trả lời và toàn hệ thống — so sánh với RAG thường",
     italic=True, size=12.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para("Ngày 28/09/2026", size=12, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, after=14)

# ======================================================================= tóm tắt
doc.add_heading("Tóm tắt kết quả", level=1)
bullet("**Tea AI trả lời đúng 78,9% câu hỏi, RAG thường chỉ đúng 21,9%.** Chênh lệch +57 điểm phần trăm, "
       "khoảng tin cậy 95% từ +46,5 đến +67,5 nên chắc chắn không phải do may mắn.")
bullet("**Nguyên nhân chính nằm ở khâu tìm tài liệu:** Tea AI đưa đúng tài liệu vào 3 đoạn đầu ở 99% câu hỏi, "
       "RAG thường chỉ 30%. Khi tìm sai tài liệu, RAG thường từ chối nhầm 45/114 câu hoặc trả lời sai.")
bullet("**Cả hai hệ thống đều biết từ chối khi tài liệu không có thông tin** (36/36 câu) và không bịa số liệu.")
bullet("**Tốc độ và chi phí gần như ngang nhau:** khoảng 1,8–1,9 giây mỗi câu và khoảng 0,5 USD cho 1.000 câu hỏi.")
bullet("**Điểm yếu còn lại:** khi người dùng hỏi bằng lời đời thường, khác hẳn từ ngữ trong tài liệu, "
       "cả hai hệ thống đều tìm kém (Tea AI 0,33) và Tea AI không còn hơn rõ rệt.")

doc.add_heading("Bảng kết quả chính", level=2)
table(["Tầng", "Chỉ số", "Tea AI", "RAG thường"], [
    ["1. Tìm tài liệu", "Context Precision@3", "0,95", "0,23"],
    ["1. Tìm tài liệu", "Context Recall@3", "0,99", "0,30"],
    ["1. Tìm tài liệu", "MRR", "0,96", "0,25"],
    ["2. Câu trả lời", "Faithfulness (bám tài liệu)", "0,99", "0,87"],
    ["2. Câu trả lời", "Response Relevancy (đúng trọng tâm)", "0,50", "0,28"],
    ["2. Câu trả lời", "Factual Correctness F1 (đúng đáp án)", "0,88", "0,23"],
    ["3. Toàn hệ thống", "Tỉ lệ trả lời đúng", "78,9%", "21,9%"],
    ["3. Toàn hệ thống", "Từ chối nhầm câu có đáp án", "5/114", "45/114"],
    ["3. Toàn hệ thống", "Từ chối đúng khi không có thông tin", "36/36", "36/36"],
    ["3. Toàn hệ thống", "Thời gian chờ (trung vị)", "1,8 giây", "1,9 giây"],
    ["3. Toàn hệ thống", "Chi phí 1.000 câu hỏi", "0,54 USD", "0,49 USD"],
    ["3. Toàn hệ thống", "Người chấm (Human evaluation)", "Chưa có", "Chưa có"],
], [3.2, 6.8, 3, 3], highlight_col=2)
note("Điểm từ 0 đến 1, càng cao càng tốt (trừ dòng từ chối nhầm, thời gian và chi phí: càng thấp càng tốt). "
     "RAG thường ở đây là bản dùng embedding đa ngữ (paraphrase-multilingual-MiniLM).")

# ======================================================================= 1. mục tiêu
doc.add_heading("1. Mục tiêu đánh giá", level=1)
para("Báo cáo trả lời ba câu hỏi, tương ứng ba tầng của một chatbot hỏi đáp tài liệu (RAG):")
bullet("**Tầng 1 – Tìm tài liệu:** hệ thống có lấy đúng đoạn tài liệu chứa câu trả lời không? "
       "Đây là tầng quan trọng nhất, vì LLM giỏi đến đâu mà nhận sai tài liệu thì vẫn trả lời sai.")
bullet("**Tầng 2 – Câu trả lời của LLM:** câu trả lời có dựa trên tài liệu, đúng trọng tâm và đúng với đáp án chuẩn không?")
bullet("**Tầng 3 – Toàn hệ thống (end-to-end):** nhìn như một sản phẩm, chatbot trả lời đúng bao nhiêu, có biết từ chối, "
       "người dùng chờ bao lâu và tốn bao nhiêu tiền?")

# ======================================================================= 2. hai hệ thống
doc.add_heading("2. Hai hệ thống được so sánh", level=1)
para("Hai hệ thống dùng **cùng kho tri thức 171 đoạn tài liệu (chunk)** về cây chè, **cùng câu hỏi**, "
     "**cùng model viết câu trả lời** và **cùng model chấm**. Chỉ khác cách tìm tài liệu và cách ra lệnh cho LLM.")
table(["Thành phần", "Tea AI", "RAG thường"], [
    ["Tìm tài liệu", "Kết hợp embedding tiếng Việt (bkai) và BM25 tiếng Việt (so khớp từ khóa, chịu được gõ không dấu)",
     "Một model embedding đa ngữ có sẵn, lấy 3 đoạn giống nhất"],
    ["Chia tài liệu", "Theo mục, giữ tiêu đề", "Như Tea AI (cùng kho)"],
    ["Cổng từ chối", "Có: câu hỏi ngoài chủ đề bị từ chối trước khi gọi LLM", "Không có"],
    ["Lời nhắc cho LLM (prompt)", "Ràng buộc: chỉ dùng tài liệu, không bịa, nói rõ phần tài liệu không nêu",
     "Chung chung: trả lời theo ngữ cảnh, không biết thì nói không biết"],
    ["Model viết câu trả lời", "gpt-oss-120b (qua Groq)", "gpt-oss-120b (qua Groq)"],
], [3.6, 6.6, 6])
para("**Model chấm:** qwen3.8-27b. Model chấm khác họ với model viết để tránh việc model tự khen câu trả lời của chính mình.")

# ======================================================================= 3. dữ liệu
doc.add_heading("3. Dữ liệu đánh giá", level=1)
table(["Bộ câu hỏi", "Số câu", "Dùng cho", "Ghi chú"], [
    ["Bộ 1000 câu (phần thuộc kho tài liệu)", "928", "Tầng 1",
     "Sinh từ chính tài liệu, mỗi câu có đáp án chuẩn và danh sách ý chính"],
    ["Bộ 928 câu, gõ không dấu", "928", "Tầng 1", "Cùng câu hỏi, bỏ dấu tiếng Việt"],
    ["Bộ 928 câu, gõ nhầm và không dấu", "928", "Tầng 1", "Đảo chỗ ký tự trong khoảng 1/4 số từ"],
    ["Bộ viết tay", "72", "Tầng 1", "Người viết và gán nhãn; một câu có thể cần nhiều đoạn"],
    ["Bộ diễn đạt lại", "60", "Tầng 1", "LLM viết lại câu hỏi bằng lời đời thường, ít trùng từ với tài liệu"],
    ["Mẫu 114 câu có đáp án", "114", "Tầng 2, 3", "Lấy đều theo 6 loại câu hỏi; không lọc theo kết quả hệ thống nào"],
    ["Câu không có thông tin", "24 + 12", "Tầng 3", "24 câu hỏi dữ liệu vùng chè không có trong kho, 12 câu ngoài chủ đề"],
    ["Mẫu đo thời gian và chi phí", "20", "Tầng 3", "Chạy lại toàn bộ luồng, gọi API thật"],
], [4.6, 1.6, 2, 8])

# ======================================================================= 4. quy trình
doc.add_heading("4. Quy trình đánh giá chi tiết", level=1)
para("Quy trình đi từ dưới lên: kiểm tra khâu tìm tài liệu trước, rồi đến câu trả lời, cuối cùng là cả hệ thống. "
     "Mỗi tầng gồm các bước sau.")

steps_reset()
doc.add_heading("4.1. Tầng 1 – Tìm tài liệu (không gọi LLM)", level=2)
step("**Chuẩn bị nhãn đúng.** Với mỗi câu hỏi, xác định các đoạn tài liệu \"liên quan\": đoạn nào chứa nguyên văn "
       "ít nhất một ý chính của đáp án chuẩn thì được tính là liên quan. Kết quả: 841 câu có 1 đoạn liên quan, "
       "87 câu có từ 2 đoạn trở lên.")
step("**Cho mỗi hệ thống tìm 5 đoạn** giống câu hỏi nhất, theo thứ tự từ cao xuống thấp.")
step("**So danh sách tìm được với nhãn đúng** và tính 5 chỉ số ở bảng dưới, chủ yếu với K = 3 "
       "vì Tea AI đưa 3 đoạn cho LLM đọc.")
step("**Lặp lại trên các bộ câu khó hơn:** gõ không dấu, gõ nhầm, câu viết tay, câu diễn đạt lại.")
step("**Kiểm tra ý nghĩa thống kê:** lấy mẫu lại 2.000 lần (bootstrap) để tính khoảng tin cậy 95% của chênh lệch.")
table(["Chỉ số", "Trả lời câu hỏi", "Cách hiểu đơn giản"], [
    ["Context Precision@K", "Đoạn đúng có nằm ở đầu danh sách không?",
     "Đoạn đúng đứng thứ 1 được điểm cao hơn đứng thứ 3"],
    ["Context Recall@K", "K đoạn lấy ra có đủ ý để trả lời không?", "Số ý chính có trong K đoạn / tổng số ý chính"],
    ["Precision@K", "Trong K đoạn lấy ra, bao nhiêu đoạn đúng?", "Số đoạn đúng / K"],
    ["Recall@K", "Lấy được bao nhiêu phần trong các đoạn đúng?", "Số đoạn đúng lấy được / tổng số đoạn đúng"],
    ["MRR", "Đoạn đúng đầu tiên đứng thứ mấy?", "Đứng thứ 1 được 1 điểm, thứ 2 được 0,5, thứ 3 được 0,33"],
], [3.6, 6, 6.6])
note("Ví dụ: câu hỏi \"Bệnh chấm xám hại chè có triệu chứng gì?\", đoạn đúng là đoạn số 45. Tea AI trả về [45, 46, 12]: "
     "đoạn đúng đứng thứ 1, MRR = 1. RAG thường trả về [88, 3, 120]: không có đoạn đúng, mọi chỉ số bằng 0.")
note("Lưu ý: hầu hết câu chỉ có 1 đoạn đúng nên Precision@3 cao nhất chỉ khoảng 0,33. Chỉ số này dùng để so sánh hai hệ thống, "
     "không đọc như tỉ lệ phần trăm tuyệt đối.")

steps_reset()
doc.add_heading("4.2. Tầng 2 – Câu trả lời của LLM (chấm theo cách của Ragas)", level=2)
step("**Lấy câu trả lời** của hai hệ thống cho 114 câu hỏi (cùng model gpt-oss-120b viết).")
step("**Model chấm tách câu trả lời thành các mệnh đề nhỏ**, mỗi mệnh đề một thông tin.")
step("**Với từng mệnh đề, model chấm trả lời hai câu hỏi:** tài liệu đã tìm có xác nhận không? "
       "Đáp án chuẩn có xác nhận không?")
step("**Kiểm tra từng ý chính của đáp án chuẩn** xem câu trả lời có nêu ý đó không.")
step("**Đo mức đúng trọng tâm:** model chấm chỉ đọc câu trả lời (không thấy câu hỏi) rồi đoán 3 câu hỏi mà nó đang trả lời. "
       "So độ giống nhau giữa 3 câu đoán và câu hỏi thật bằng embedding tiếng Việt.")
step("**Tính 3 chỉ số** ở bảng dưới, rồi tính khoảng tin cậy 95% cho chênh lệch giữa hai hệ thống.")
table(["Chỉ số", "Trả lời câu hỏi", "Cách tính"], [
    ["Faithfulness", "Câu trả lời có dựa trên tài liệu đã tìm không, hay tự bịa?",
     "Số mệnh đề được tài liệu xác nhận / tổng số mệnh đề"],
    ["Response Relevancy", "Câu trả lời có đúng trọng tâm câu hỏi không?",
     "Độ giống giữa câu hỏi đoán ra và câu hỏi thật (0 nếu câu trả lời né tránh)"],
    ["Factual Correctness", "Câu trả lời có đúng so với đáp án chuẩn không?",
     "Precision: mệnh đề đúng theo đáp án / tổng mệnh đề. Recall: ý chính được nêu / tổng ý chính. F1: trung bình điều hòa của hai số"],
], [3.6, 5.6, 7])
note("Ví dụ minh họa: câu trả lời có 4 mệnh đề, tài liệu xác nhận 3 thì Faithfulness = 3/4 = 0,75. "
     "Đáp án chuẩn có 5 ý chính, câu trả lời nêu được 4 thì Recall = 4/5 = 0,8.")
note("Faithfulness và Factual Correctness phải đọc cùng nhau: nếu hệ thống tìm sai tài liệu nhưng LLM bám sát tài liệu sai đó, "
     "Faithfulness vẫn cao mà câu trả lời vẫn sai.")

steps_reset()
doc.add_heading("4.3. Tầng 3 – Toàn hệ thống (end-to-end)", level=2)
step("**Độ chính xác:** model chấm xếp mỗi câu trả lời vào một trong ba mức: đúng, đúng một phần, sai. "
       "Câu bị từ chối nhầm tính là sai.")
step("**Khả năng từ chối:** hỏi 36 câu mà kho tài liệu không có câu trả lời. Đếm số câu hệ thống từ chối đúng "
       "và số câu tự bịa số liệu.")
step("**Thời gian chờ:** chạy lại toàn bộ luồng (tìm tài liệu rồi gọi LLM) cho 20 câu, đo riêng từng phần.")
step("**Chi phí:** lấy số token thật do Groq trả về, nhân với giá của gpt-oss-120b "
       "(0,15 USD cho 1 triệu token vào, 0,60 USD cho 1 triệu token ra).")
step("**Người chấm:** chuẩn bị phiếu 30 cặp câu trả lời, ẩn tên hệ thống (A/B) để người chấm điểm 1–5. "
       "Phần này đang chờ người chấm điền.")

# ======================================================================= 5. kết quả tầng 1
doc.add_heading("5. Kết quả tầng 1 – Tìm tài liệu", level=1)
doc.add_heading("5.1. Bộ 928 câu gốc (K = 3)", level=2)
table(["Hệ thống", "Context Precision", "Context Recall", "Precision@3", "Recall@3", "MRR"], [
    ["RAG thường (all-MiniLM, tiếng Anh)", "0,179", "0,235", "0,082", "0,222", "0,192"],
    ["RAG thường (đa ngữ)", "0,233", "0,301", "0,109", "0,291", "0,252"],
    ["Chỉ embedding tiếng Việt (bkai)", "0,781", "0,878", "0,314", "0,856", "0,793"],
    ["Chỉ BM25 tiếng Việt", "0,949", "0,982", "0,349", "0,958", "0,954"],
    ["**Tea AI (kết hợp)**", "**0,953**", "**0,991**", "**0,357**", "**0,972**", "**0,957**"],
], [5, 2.4, 2.3, 2.2, 2.1, 2.1])
note("Tea AI hơn RAG thường đa ngữ khoảng +0,7 ở mọi chỉ số; khoảng tin cậy 95% hoàn toàn dương "
     "(ví dụ Context Precision +0,720 [+0,695; +0,746]).")

doc.add_heading("5.2. Các tình huống khó hơn (Tea AI so với RAG thường đa ngữ)", level=2)
table(["Bộ câu hỏi", "Số câu", "Tea AI (CP / CR)", "RAG thường (CP / CR)", "Tea AI hơn chắc chắn?"], [
    ["Câu gốc có dấu", "928", "0,95 / 0,99", "0,23 / 0,30", "Có"],
    ["Gõ không dấu", "928", "0,94 / 0,97", "0,03 / 0,05", "Có"],
    ["Gõ nhầm và không dấu", "928", "0,81 / 0,86", "0,02 / 0,03", "Có"],
    ["Viết tay (người gán nhãn)", "72", "0,94 / 0,77", "0,59 / 0,47", "Có (*)"],
    ["Diễn đạt lại bằng lời đời thường", "60", "0,26 / 0,33", "0,17 / 0,25", "Không"],
], [5, 1.6, 3.2, 3.6, 2.8])
note("CP = Context Precision@3, CR = Context Recall@3. (*) Tea AI được hiệu chỉnh trên bộ viết tay nên kết quả của Tea AI "
     "ở bộ này có thể lạc quan. Ở bộ diễn đạt lại, khoảng tin cậy của chênh lệch chứa số 0 nên chưa kết luận được.")

doc.add_heading("5.3. Theo loại câu hỏi (Context Precision / Context Recall, câu gốc)", level=2)
table(["Loại câu hỏi", "Số câu", "Tea AI", "RAG thường"], [
    ["Hỏi đủ ý (completeness)", "171", "0,98 / 0,99", "0,19 / 0,26"],
    ["Hỏi trực tiếp (direct_grounded)", "171", "0,99 / 1,00", "0,29 / 0,37"],
    ["Hỏi chuyên môn (domain_question)", "171", "0,99 / 1,00", "0,19 / 0,25"],
    ["Trích số liệu (numeric_extraction)", "73", "0,99 / 1,00", "0,29 / 0,37"],
    ["Diễn đạt lại (paraphrase)", "171", "0,99 / 1,00", "0,26 / 0,33"],
    ["Ràng buộc nguồn (source_constrained)", "171", "0,80 / 0,96", "0,22 / 0,27"],
], [6.4, 1.8, 3.8, 3.8])
note("Loại \"ràng buộc nguồn\" là điểm yếu của Tea AI: vẫn tìm được đoạn đúng (Recall 0,96) nhưng hay xếp ở vị trí 2–3 "
     "thay vì vị trí đầu.")

# ======================================================================= 6. kết quả tầng 2
doc.add_heading("6. Kết quả tầng 2 – Câu trả lời của LLM (114 câu)", level=1)
table(["Chỉ số", "Tea AI", "RAG thường", "Chênh lệch [KTC 95%]"], [
    ["Faithfulness", "0,994", "0,866", "+0,141 [+0,073; +0,217]"],
    ["Response Relevancy", "0,497", "0,278", "+0,219 [+0,160; +0,279]"],
    ["Factual Correctness – Precision", "0,926", "0,363", "+0,516 [+0,413; +0,615]"],
    ["Factual Correctness – Recall", "0,869", "0,260", "+0,608 [+0,511; +0,696]"],
    ["**Factual Correctness – F1**", "**0,884**", "**0,228**", "**+0,646 [+0,557; +0,728]**"],
], [5.6, 2.4, 2.6, 5.6])
note("Faithfulness và Precision chỉ tính trên câu không bị từ chối (Tea AI 104 câu, RAG thường 69 câu). "
     "Câu bị từ chối nhầm được tính 0 điểm ở Response Relevancy, Recall và F1. Response Relevancy là độ giống giữa hai câu "
     "hỏi nên thường không cao; chỉ nên dùng để so sánh hai hệ thống.")

doc.add_heading("Theo loại câu hỏi (Factual Correctness F1 / Faithfulness)", level=3)
table(["Loại câu hỏi", "Số câu", "Tea AI", "RAG thường"], [
    ["Hỏi đủ ý", "21", "0,93 / 1,00", "0,21 / 1,00"],
    ["Hỏi trực tiếp", "21", "0,90 / 0,97", "0,33 / 0,92"],
    ["Hỏi chuyên môn", "21", "0,91 / 0,99", "0,18 / 0,64"],
    ["Trích số liệu", "9", "0,75 / 1,00", "0,29 / 0,97"],
    ["Diễn đạt lại", "21", "0,85 / 1,00", "0,22 / 0,91"],
    ["Ràng buộc nguồn", "21", "0,89 / 1,00", "0,18 / 0,83"],
], [6.4, 1.8, 3.8, 3.8])

# ======================================================================= 7. kết quả tầng 3
doc.add_heading("7. Kết quả tầng 3 – Toàn hệ thống", level=1)
doc.add_heading("7.1. Độ chính xác câu trả lời (114 câu có đáp án)", level=2)
table(["Chỉ số", "Tea AI", "RAG thường"], [
    ["Trả lời đúng", "78,9%", "21,9%"],
    ["Đúng hoặc đúng một phần", "90,4%", "25,4%"],
    ["Từ chối nhầm câu có đáp án", "5/114 (4%)", "45/114 (39%)"],
], [7, 4, 4])
note("Chênh lệch tỉ lệ trả lời đúng: +57,0 điểm phần trăm, khoảng tin cậy 95% [+46,5; +67,5].")

doc.add_heading("7.2. Khi tài liệu không có thông tin (No-answer accuracy)", level=2)
table(["Bộ câu", "Tea AI: từ chối đúng", "Tea AI: bịa số", "RAG thường: từ chối đúng", "RAG thường: bịa số"], [
    ["24 câu thiếu dữ liệu vùng chè", "24/24", "0", "24/24", "0"],
    ["12 câu ngoài chủ đề", "12/12", "0", "12/12", "0"],
    ["**Tổng**", "**36/36**", "**0**", "**36/36**", "**0**"],
], [5, 2.9, 2.3, 3.2, 2.6])
note("Tea AI từ chối nhờ cổng từ chối và prompt ràng buộc. RAG thường không có cổng nhưng LLM tự nói \"không biết\" khi "
     "tài liệu không liên quan, nên hai hệ thống ngang nhau ở tiêu chí này.")

doc.add_heading("7.3. Thời gian chờ và chi phí (20 câu, gọi API thật)", level=2)
table(["Chỉ số", "Tea AI", "RAG thường"], [
    ["Tìm tài liệu, trung vị", "62 ms", "31 ms"],
    ["LLM viết câu trả lời, trung vị", "1,72 giây", "1,88 giây"],
    ["Tổng thời gian chờ, trung vị", "1,80 giây", "1,90 giây"],
    ["Tổng thời gian chờ, 90% số câu dưới", "3,09 giây", "3,11 giây"],
    ["Token đầu vào trung bình", "1.557", "680"],
    ["Token đầu ra trung bình", "511", "642"],
    ["Chi phí mỗi câu hỏi", "0,00054 USD", "0,00049 USD"],
    ["Chi phí 1.000 câu hỏi", "0,54 USD", "0,49 USD"],
], [7, 4, 4])
note("Tea AI dùng nhiều token đầu vào hơn (prompt dài hơn) nhưng viết câu trả lời ngắn hơn, nên tổng chi phí gần bằng RAG thường. "
     "Thời gian LLM phụ thuộc tải của Groq lúc đo. Chi phí chưa gồm model chấm (chỉ dùng khi đánh giá).")

doc.add_heading("7.4. Người chấm (Human evaluation)", level=2)
para("Chưa có kết quả. Phiếu **docs/phieu_cham_tay_cap_tra_loi.csv** gồm 30 cặp câu trả lời, ẩn tên hệ thống (A/B). "
     "Người chấm cho điểm 1–5 mỗi câu trả lời, sau đó chạy lệnh ở phụ lục để tính điểm theo người và mức đồng thuận "
     "giữa người chấm và model chấm. Đây là bước cần làm để chứng minh model chấm đáng tin.")

# ======================================================================= 8. nhận xét
doc.add_heading("8. Nhận xét", level=1)
doc.add_heading("Điểm mạnh của Tea AI", level=3)
bullet("Tìm đúng tài liệu gần như mọi câu hỏi dùng từ ngữ của tài liệu, kể cả khi người dùng gõ không dấu hoặc gõ nhầm.")
bullet("Nhờ tìm đúng tài liệu, câu trả lời đúng gấp khoảng 3,6 lần RAG thường (78,9% so với 21,9%).")
bullet("Bám sát tài liệu (Faithfulness 0,99), không bịa số liệu.")
bullet("Không tốn thêm thời gian hay chi phí đáng kể so với RAG thường.")
doc.add_heading("Điểm cần cải thiện", level=3)
bullet("Câu hỏi diễn đạt bằng lời đời thường: Hit@3 chỉ còn 0,33. Hướng xử lý: tăng trọng số embedding tiếng Việt trong "
       "phần kết hợp, hoặc viết lại câu hỏi trước khi tìm, sau khi có bộ câu hỏi đã được người xác nhận.")
bullet("Cổng từ chối chặn nhầm 5/114 câu có đáp án (4%). Cần xem lại ngưỡng của cổng.")
bullet("Câu hỏi \"ràng buộc nguồn\" và câu cần nhiều đoạn: đoạn đúng hay nằm ở vị trí 2–3 hoặc 3 đoạn không đủ ý.")

# ======================================================================= 9. hạn chế
doc.add_heading("9. Hạn chế của đánh giá", level=1)
bullet("Chỉ số tầng 2 làm theo định nghĩa của Ragas nhưng do nhóm tự cài đặt và chỉ dùng một model chấm; "
       "chưa đối chiếu với người chấm.")
bullet("Tầng 1 xác định đoạn liên quan bằng so khớp văn bản với ý chính, không dùng LLM; đoạn nói cùng ý bằng từ khác "
       "có thể bị bỏ sót, nên kết quả là cận dưới.")
bullet("Bộ 1000 câu được sinh từ chính tài liệu nên thuận lợi cho khâu tìm tài liệu; bộ diễn đạt lại còn nhãn nhiễu.")
bullet("Tầng 2 và 3 dùng mẫu 114 câu (giới hạn hạn mức miễn phí của Groq); thời gian và chi phí đo trên 20 câu.")
bullet("Giữa chừng, lời nhắc cho model chấm được rút gọn để xử lý câu trả lời dài (khoảng 150/228 câu chấm bằng bản cũ). "
       "Các chỉ số là tỉ lệ nên ảnh hưởng nhỏ.")
bullet("So với báo cáo trước, tỉ lệ từ chối nhầm của Tea AI cao hơn (5/114 thay vì 1/67) vì bộ 67 câu cũ chỉ chọn "
       "những câu Tea AI đã trả lời được. Kết quả trong báo cáo này dùng mẫu không thiên lệch.")

# ======================================================================= phụ lục
doc.add_heading("Phụ lục – Cách chạy lại đánh giá", level=1)
note("Nếu bị dừng giữa chừng, chạy lại cùng lệnh để tiếp tục (kết quả từng câu đã được lưu).")
table(["Việc", "Lệnh", "Kết quả ghi ra"], [
    ["Tầng 1", "python -m rag.evaluation.run_retrieval_metrics", "docs/RAG_RETRIEVAL_METRICS.md"],
    ["Tầng 2 và 3", "python -m backend.evaluation.ragas_style_eval", "docs/RAG_ANSWER_E2E_EVALUATION.md"],
    ["Người chấm (sau khi điền phiếu)", "python -m backend.evaluation.human_agreement", "In ra màn hình"],
], [3.6, 7.2, 5.4], font=10.5)
last = doc.paragraphs[-1]  # Word bắt buộc có đoạn sau bảng cuối: thu nhỏ để không tràn sang trang mới
last.paragraph_format.space_after = Pt(0)
last.paragraph_format.line_spacing = Pt(1)
last.add_run().font.size = Pt(1)

doc.save(OUT)
print("saved", OUT)
