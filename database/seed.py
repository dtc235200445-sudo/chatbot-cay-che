import json
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import engine, SessionLocal
from database.models import (
    Base,
    User,
    Document,
    KnowledgeChunk,
    TeaDisease,
    TeaCultivationTopic,
    WeatherData,
)

# Đường dẫn tuyệt đối để chạy được từ bất kỳ thư mục làm việc nào
DEFAULT_KB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json")


def seed_database(kb_json_path: str = DEFAULT_KB_PATH):
    print("========================================")
    print("STARTING DATABASE SEED PROCESS")
    print("========================================")

    # 1. Initialize Schema
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Load Knowledge Base JSON
        with open(kb_json_path, "r", encoding="utf-8") as f:
            kb_chunks = json.load(f)

        print(f"Loaded {len(kb_chunks)} chunks from {kb_json_path}")

        # 2. Seed Documents
        doc_definitions = [
            {
                "document_code": "TL1_Tea_Technical_Guideline",
                "title": "Tài liệu kỹ thuật trồng và chăm sóc chè (TL1)",
                "source": "Tài liệu kỹ thuật trồng và chăm sóc chè (TL1)",
                "source_type": "technical_document",
                "dataset": "TL1_Tea_Technical_Guideline",
                "version": "1.0",
                "language": "vi",
                "region": "Việt Nam",
                "year": None,
                "description": "Tài liệu hướng dẫn kỹ thuật nông nghiệp trồng, đốn, bón phân và chăm sóc cây chè Việt Nam."
            },
            {
                "document_code": "TeaLeafDiseaseBD",
                "title": "TeaLeafDiseaseBD: Annotated smartphone images and lesion-level labels of tea leaf diseases from Bangladesh",
                "source": "TeaLeafDiseaseBD: Annotated smartphone images and lesion-level labels of tea leaf diseases from Bangladesh",
                "source_type": "dataset_documentation",
                "dataset": "TeaLeafDiseaseBD",
                "version": "2",
                "language": "vi",
                "region": "Bangladesh",
                "year": 2025,
                "description": "Tài liệu mô tả bộ dữ liệu 13.085 ảnh lá chè bị bệnh thu thập tại Bangladesh."
            },
            {
                "document_code": "LaiChau_Tea_Technical_Guideline",
                "title": "Quyết định 450/QĐ-SNNMT Lai Châu 2025",
                "source": "450-qd-ban-hanh-huong-dan-trong-cheban-hanh-24.7(1).pdf",
                "source_type": "official_technical_document",
                "dataset": "LaiChau_Tea_Technical_Guideline",
                "version": "2025",
                "language": "vi",
                "region": "Lai Châu",
                "year": 2025,
                "description": "Quyết định ban hành Hướng dẫn kỹ thuật trồng và chăm sóc cây chè tỉnh Lai Châu."
            }
        ]

        # Nguồn tri thức bên ngoài (data/external/*.json): URL, giấy phép và trích dẫn được ghi vào mô tả tài liệu
        for ext_file in sorted(Path(__file__).resolve().parent.parent.joinpath("data", "external").glob("*.json")):
            ext = json.loads(ext_file.read_text(encoding="utf-8"))
            d = ext["document"]
            doc_definitions.append({
                "document_code": d["document_code"],
                "title": d["title"],
                "source": d["source"],
                "source_type": d["source_type"],
                "dataset": ext["dataset"],
                "version": str(d["version"]),
                "language": "vi",
                "region": d.get("region"),
                "year": d.get("year"),
                "description": (
                    f"{d['description']} Giấy phép: {d['license']}. URL: {d['url']}. "
                    f"Truy cập: {d['accessed']}. Trích dẫn: {d['citation']}"
                ),
            })

        doc_map = {}
        for doc_data in doc_definitions:
            existing_doc = db.query(Document).filter_by(document_code=doc_data["document_code"]).first()
            if not existing_doc:
                doc_obj = Document(**doc_data)
                db.add(doc_obj)
                db.flush()
                doc_map[doc_data["document_code"]] = doc_obj.id
                print(f"Created Document: '{doc_data['document_code']}' (ID: {doc_obj.id})")
            else:
                doc_map[doc_data["document_code"]] = existing_doc.id
                print(f"Existing Document found: '{doc_data['document_code']}' (ID: {existing_doc.id})")

        # 3. Seed Knowledge Chunks
        chunk_inserted_count = 0
        for item in kb_chunks:
            chunk_id = item["chunk_id"]
            existing_chunk = db.query(KnowledgeChunk).filter_by(chunk_id=chunk_id).first()
            
            # Map to document_id
            dataset_name = item.get("dataset", "")
            doc_id = doc_map.get(dataset_name)
            if not doc_id:
                # Fallback matching source string
                if "TL1" in item.get("source", ""):
                    doc_id = doc_map["TL1_Tea_Technical_Guideline"]
                elif "TeaLeafDiseaseBD" in item.get("source", ""):
                    doc_id = doc_map["TeaLeafDiseaseBD"]
                else:
                    doc_id = doc_map["LaiChau_Tea_Technical_Guideline"]

            meta = item.get("metadata", {})
            page_val = meta.get("page") if isinstance(meta, dict) else None
            section_val = meta.get("section") if isinstance(meta, dict) else None
            year_val = meta.get("year") if isinstance(meta, dict) else None

            if not existing_chunk:
                chunk_obj = KnowledgeChunk(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    title=item["title"],
                    content=item["content"],
                    source=item["source"],
                    source_type=item["source_type"],
                    category=item["category"],
                    topic=item.get("topic", item["title"]),
                    disease=item.get("disease", ""),
                    dataset=item.get("dataset", ""),
                    version=str(item.get("version", "")),
                    language=item.get("language", "vi"),
                    region=item.get("region", meta.get("region") if isinstance(meta, dict) else ""),
                    section=section_val,
                    page=page_val,
                    year=year_val,
                    original_chunk_id=meta.get("original_chunk_id") if isinstance(meta, dict) else None
                )
                db.add(chunk_obj)
                chunk_inserted_count += 1

        db.commit()
        total_db_chunks = db.query(KnowledgeChunk).count()
        print(f"Inserted {chunk_inserted_count} new chunks. Total DB chunks: {total_db_chunks}")

        # 4. Seed Diseases (Extracted strictly from KB)
        disease_names = [
            ("Rệp xanh", "Empoasca flavescens", "Lá non quăn queo, mật đọng đen bám mặt lá, làm suy giảm quang hợp."),
            ("Bọ trĩ", "Physothrips setiventris", "Lá già bạc màu, xuất hiện vết sần li ti màu nâu đen ở mặt dưới lá."),
            ("Nhện đỏ", "Oligonychus coffeae", "Mặt trên lá biến vàng cam, sau chuyển nâu sẫm và rụng sớm."),
            ("Bệnh thối búp", "Exobasidium vexans", "Búp chè biến dạng, đốm phồng màu mỡ lợn sau chuyển xám trắng."),
            ("Bệnh đốm nâu", "Colletotrichum camelliae", "Đốm bệnh hình tròn hoặc bất định màu nâu, xuất hiện trên lá bánh tẻ."),
            ("Bệnh chấm xám", "Pestalotiopsis theae", "Đốm màu xám nhạt với viền nâu đậm, lá khô và rụng."),
            ("Red Spider", "Oligonychus coffeae", "Nhện đỏ hại chè trong bộ dữ liệu TeaLeafDiseaseBD."),
            ("Brown Blight", "Colletotrichum camelliae", "Bệnh thối nâu lá chè trong bộ dữ liệu TeaLeafDiseaseBD."),
            ("Gray Blight", "Pestalotiopsis theae", "Bệnh chấm xám lá chè trong bộ dữ liệu TeaLeafDiseaseBD."),
            ("Helopeltis", "Helopeltis theivora", "Bọ xít muỗi gây đốm đen thâm trên búp non chè."),
            ("Algal Leaf Spot", "Cephaleuros virescens", "Bệnh đốm tảo sinh ra các đốm nhung màu cam trên lá chè."),
            ("Red Rust", "Cephaleuros virescens", "Bệnh rỉ sắt đỏ trên thân và lá chè.")
        ]

        for d_name, sc_name, symp in disease_names:
            if not db.query(TeaDisease).filter_by(name=d_name).first():
                db.add(TeaDisease(name=d_name, scientific_name=sc_name, symptoms=symp, severity="medium"))
        db.commit()

        # 5. Seed Users
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(
                username="admin",
                email="admin@teascholar.ai",
                password_hash="pbkdf2:sha256:dummy_admin_hash",
                full_name="System Administrator",
                role="admin",
                is_active=True
            ))
        if not db.query(User).filter_by(username="demo_user").first():
            db.add(User(
                username="demo_user",
                email="user@teascholar.ai",
                password_hash="pbkdf2:sha256:dummy_user_hash",
                full_name="Nông dân Phú Thọ",
                role="user",
                is_active=True
            ))
        db.commit()

        # 6. Seed Weather Locations
        regions_weather = [
            ("Phú Thọ", 21.3167, 105.2167, 28.0, 78.0, 20.0, 12.0, "Partly cloudy"),
            ("Thái Nguyên", 21.5928, 105.8442, 27.5, 80.0, 15.0, 10.0, "Sunny"),
            ("Lâm Đồng", 11.9404, 108.4583, 22.0, 85.0, 40.0, 8.0, "Cloudy"),
            ("Lai Châu", 22.3964, 103.4589, 24.0, 82.0, 30.0, 14.0, "Rain probability 30%")
        ]
        for reg, lat, lon, temp, hum, rain, wind, cond in regions_weather:
            if not db.query(WeatherData).filter_by(region=reg).first():
                db.add(WeatherData(
                    region=reg, latitude=lat, longitude=lon,
                    temperature=temp, humidity=hum, rainfall=rain,
                    wind_speed=wind, weather_condition=cond
                ))
        db.commit()

        print("========================================")
        print("DATABASE SEED COMPLETED SUCCESSFULLY")
        print("========================================")

    except Exception as e:
        db.rollback()
        print(f"SEED ERROR: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
