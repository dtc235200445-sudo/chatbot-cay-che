"""
Tạo các tệp dữ liệu tri thức từ nguồn bên ngoài trong data/external/.

Mỗi đoạn (chunk) có nội dung tiếng Việt do người soạn dịch/tóm lược từ nguồn gốc và kèm:
  - trích nguyên văn tiếng Anh (`original_quote`) để đối chiếu bản dịch,
  - nguồn, URL, giấy phép và ngày truy cập ở cấp tài liệu.
Chỉ đưa vào các số liệu đã đọc trực tiếp từ nguồn; không suy diễn thêm.

Chạy:  python scripts/build_external_sources.py
Sau đó: python scripts/build_knowledge_base.py && python database/seed.py && python -m rag.ingest
"""
import json
import pathlib

ACCESSED = "2026-09-19"
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "external"


def make_doc(dataset, source, version, year, region, url, license_, citation, title, description, chunks):
    return {
        "dataset": dataset,
        "document": {
            "document_code": dataset,
            "title": title,
            "source": source,
            "source_type": "scientific_reference",
            "version": version,
            "year": year,
            "region": region,
            "description": description,
            "url": url,
            "license": license_,
            "citation": citation,
            "accessed": ACCESSED,
        },
        "chunks": chunks,
    }


def chunk(title, content, category, quote, section, region, year):
    return {
        "title": title,
        "content": content,
        "category": category,
        "disease": "",
        "metadata": {
            "section": section,
            "page": None,
            "region": region,
            "year": year,
            "original_quote": quote,
        },
    }


ECO_URL = "https://ecocrop.apps.fao.org/ecocrop/srv/en/cropView?id=599"
ECO_CITE = (
    "FAO. EcoCrop: Camellia sinensis (L.) O. Kuntze (tea). Truy cập ngày 19/09/2026. " + ECO_URL
    + " Giấy phép: CC-BY-4.0 (theo điều khoản cơ sở dữ liệu của FAO). Nội dung là bản dịch/tóm lược tiếng Việt; "
    "FAO không tham gia hay xác nhận việc sử dụng này."
)

ECO_CHUNKS = [
    chunk(
        "Cây chè (Camellia sinensis) theo FAO EcoCrop — đặc điểm chung",
        "Theo cơ sở dữ liệu FAO EcoCrop, chè có tên khoa học Camellia sinensis (L.) O. Kuntze, họ Theaceae; "
        "tên gọi thông thường gồm cha, chah, tea, tee, ti. Hiện nay chè được trồng trong khoảng từ 40° vĩ Bắc đến 33° vĩ Nam. "
        "Đây là số liệu tổng quan quốc tế, không thay thế khuyến cáo kỹ thuật riêng của từng vùng trồng ở Việt Nam.",
        "general_knowledge",
        '"Camellia sinensis"; "Authority: (L.) O. Kuntze"; "Common names: cha, chah, tea, tee, ti"; '
        '"it is now grown between 40°N and 33°S"',
        "Đặc điểm chung", "Quốc tế", None,
    ),
    chunk(
        "Nhiệt độ gây chết đối với cây chè (FAO EcoCrop)",
        "Theo FAO EcoCrop, nhiệt độ gây chết đối với chè là từ 0 đến −5°C tùy giống: chè var. sinensis chịu được −5°C, "
        "trong khi lá của chè var. assamica bị chết ở 0°C.",
        "ecological_conditions",
        '"KILLING T.: 0 to -5°C depending on the cultivar, var. sinensis withstands -5°C, whereas the leaves of '
        'var. assamica are killed by 0°C."',
        "Nhiệt độ", "Quốc tế", None,
    ),
    chunk(
        "Độ cao và vĩ độ thích hợp trồng chè (FAO EcoCrop)",
        "Theo FAO EcoCrop, chè có thể được trồng ở vùng đất thấp cận nhiệt đới và lên đến khoảng 1.800 m, "
        "thậm chí 2.400–3.000 m ở vùng nhiệt đới. Phần lớn sản lượng chè được sản xuất ở độ cao từ 750 đến 1.500 m.",
        "ecological_conditions",
        '"Tea can be grown in subtropical lowland and up to about 1800 m or even 2400-3000 m in the tropics"; '
        '"the majority of the production takes place between 750 and 1500 m"',
        "Độ cao", "Quốc tế", None,
    ),
    chunk(
        "Độ ẩm và hệ rễ của cây chè (FAO EcoCrop)",
        "Theo FAO EcoCrop, độ ẩm quá thấp hoặc quá cao đều có thể làm giảm năng suất chè và tạo điều kiện cho sâu bệnh phát sinh. "
        "Cây chè có rễ cọc hoặc hệ rễ xiên; rễ cọc có thể ăn sâu tới 3 m nhưng độ sâu thường gặp là 1,5 m.",
        "ecological_conditions",
        '"Too low and too high humidity can reduce yields and encourage disease."; '
        '"It has a taproot or oblique root system. The taproot may reach 3 m deep, but 1.5 is the usual."',
        "Độ ẩm và rễ", "Quốc tế", None,
    ),
    chunk(
        "Chu kỳ sinh trưởng, tuổi thọ và thời gian bắt đầu thu hái chè (FAO EcoCrop)",
        "Theo FAO EcoCrop, chu kỳ sinh trưởng của chè là 240–365 ngày. Cây có thể bắt đầu cho thu hái lá sau 2–5 năm "
        "và đạt tối đa ở năm thứ 7–10. Đời sống kinh tế của cây khoảng 40 năm, đôi khi các đồi chè được giữ trong sản xuất "
        "60–70 năm hoặc thậm chí 100 năm.",
        "cultivation_technique",
        '"The growth cycle is 240-365 days"; "Harvest of leaves may begin after 2-5 years and reaches a maximum at 7-10 years."; '
        '"The economic life of the plant is about 40 years, but sometimes the shrubs are kept in production 60-70, or even 100 years."',
        "Chu kỳ và tuổi thọ", "Quốc tế", None,
    ),
    chunk(
        "Lượng dưỡng chất chè lấy đi khỏi ruộng và năng suất tối ưu (FAO EcoCrop)",
        "Theo FAO EcoCrop, mỗi tấn chè lấy đi khỏi ruộng khoảng 45–60 kg N, 4–7 kg P và 20–30 kg K. "
        "Năng suất tối ưu khoảng 3,0 tấn/ha; ở châu Phi, năng suất trung bình dao động từ 0,5 đến 2,0 tấn/ha. "
        "Đây là số liệu tham khảo quốc tế, cần đối chiếu với định mức bón phân trong tài liệu kỹ thuật của Việt Nam.",
        "fertilization",
        '"One ton of tea removes 45-60 kg N, 4-7 kg P and 20-30 kg K from the field."; '
        '"Optimum yield is about 3.0 t/ha, in Africa average yields are between 0.5-2.0 t/ha."',
        "Dưỡng chất và năng suất", "Quốc tế", None,
    ),
]

TANG_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC7000836/"
TANG_CITE = (
    "Tang S., Liu Y., Zheng N., Li Y., Ma Q., Xiao H., Zhou X., Xu X., Jiang T., He P., Wu L. (2020). Temporal variation in "
    "nutrient requirements of tea (Camellia sinensis) in China based on QUEFTS analysis. Scientific Reports. "
    "DOI: 10.1038/s41598-020-57809-x. " + TANG_URL + " Giấy phép: CC BY 4.0. "
    "Nội dung là bản dịch/tóm lược tiếng Việt; số liệu từ Trung Quốc."
)

TANG_CHUNKS = [
    chunk(
        "Nhu cầu N, P, K của chè theo vụ (Tang và cộng sự, 2020)",
        "Theo nghiên cứu của Tang và cộng sự (2020) tại Trung Quốc, để sản xuất 1.000 kg chè cần: "
        "vụ xuân 12,2 kg N, 1,2 kg P và 3,9 kg K; vụ hè 9,1 kg N, 0,8 kg P và 3,1 kg K; "
        "vụ thu 8,8 kg N, 1,0 kg P và 3,2 kg K. Nhu cầu đạm (N) cao nhất ở vụ xuân.",
        "fertilization",
        '"12.2 kg nitrogen (N), 1.2 kg phosphorus (P), and 3.9 kg potassium (K)" (spring); '
        '"9.1 kg N, 0.8 kg P, and 3.1 kg K" (summer); "8.8 kg N, 1.0 kg P, and 3.2 kg K" (autumn)',
        "Nhu cầu dưỡng chất theo vụ", "Trung Quốc", 2020,
    ),
    chunk(
        "Tỷ lệ N:P:K tối ưu cho chè theo vụ (Tang và cộng sự, 2020)",
        "Theo Tang và cộng sự (2020), tỷ lệ N:P:K tối ưu (quy P về 1) là 10,1:1:3,2 đối với chè vụ xuân, "
        "11,3:1:3,8 đối với vụ hè và 9,2:1:3,4 đối với vụ thu. Tỷ lệ đạm và kali so với lân khác nhau giữa các vụ.",
        "fertilization",
        '"10.1:1:3.2" (spring); "11.3:1:3.8" (summer); "9.2:1:3.4" (autumn)',
        "Tỷ lệ N:P:K", "Trung Quốc", 2020,
    ),
    chunk(
        "Phạm vi và giới hạn áp dụng của nghiên cứu nhu cầu dưỡng chất chè (Tang và cộng sự, 2020)",
        "Nghiên cứu của Tang và cộng sự (2020, Scientific Reports) dựa trên 21 thí nghiệm ngoài đồng tại tám tỉnh của Trung Quốc "
        "(An Huy, Hồ Bắc, Vân Nam, Tứ Xuyên, Quý Châu, Hồ Nam, Chiết Giang, Phúc Kiến) thuộc bốn vùng chè; số liệu 2016–2018 dùng "
        "để xây dựng mô hình QUEFTS và số liệu 2019 dùng để kiểm chứng. Do điều kiện đất và giống khác Việt Nam, các số liệu này chỉ "
        "mang tính tham khảo, không thay thế định mức bón phân trong tài liệu kỹ thuật của Việt Nam.",
        "fertilization",
        '"21 field experiments"; "Eight provinces (Anhui, Hubei, Yunnan, Sichuan, Guizhou, Hunan, Zhejiang, Fujian)"; '
        '"2016-2018 data for model construction and 2019 for validation"',
        "Phạm vi nghiên cứu", "Trung Quốc", 2020,
    ),
]

FILES = {
    "fao_ecocrop_camellia_sinensis.json": make_doc(
        "FAO_EcoCrop_Camellia_sinensis",
        "FAO EcoCrop — Camellia sinensis (tea)", "2026-09-19", None, "Quốc tế", ECO_URL, "CC-BY-4.0", ECO_CITE,
        "FAO EcoCrop — Camellia sinensis (L.) O. Kuntze (tea)",
        "Yêu cầu sinh thái và số liệu sản xuất của cây chè theo cơ sở dữ liệu EcoCrop của FAO.",
        ECO_CHUNKS,
    ),
    "tang2020_tea_nutrient_requirements.json": make_doc(
        "Tang2020_Tea_Nutrient_QUEFTS",
        "Tang et al. (2020), Scientific Reports — Nhu cầu dưỡng chất của chè (QUEFTS)", "2020", 2020, "Trung Quốc",
        TANG_URL, "CC-BY-4.0", TANG_CITE,
        "Temporal variation in nutrient requirements of tea (Camellia sinensis) in China based on QUEFTS analysis",
        "Bài báo truy cập mở về nhu cầu N, P, K của chè theo vụ dựa trên 21 thí nghiệm tại Trung Quốc.",
        TANG_CHUNKS,
    ),
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, obj in FILES.items():
        (OUT_DIR / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{name}: {len(obj['chunks'])} chunk")


if __name__ == "__main__":
    main()
