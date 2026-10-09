import json
import sys
from pathlib import Path
from sqlalchemy import inspect
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
    ChatSession,
    ChatMessage
)

def run_database_tests(kb_json_path: str = str(Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json")):
    print("========================================")
    print("DATABASE AUDIT & INTEGRITY VERIFICATION")
    print("========================================")

    test_results = {}

    # Test 1: Connection Test
    try:
        connection = engine.connect()
        connection.close()
        test_results["Database connection"] = "PASS"
        print("[PASS] 1. Database Connection")
    except Exception as e:
        test_results["Database connection"] = f"FAIL ({e})"
        print(f"[FAIL] 1. Database Connection: {e}")

    # Test 2: Table Existence & Schema Test
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    expected_tables = [
        "users", "documents", "knowledge_chunks",
        "tea_diseases", "tea_cultivation_topics",
        "weather_data", "chat_sessions", "chat_messages"
    ]
    missing_tables = [t for t in expected_tables if t not in existing_tables]

    if not missing_tables:
        test_results["Schema validation"] = "PASS"
        print(f"[PASS] 2. Schema Validation (All {len(expected_tables)} tables present)")
    else:
        test_results["Schema validation"] = f"FAIL (Missing: {missing_tables})"
        print(f"[FAIL] 2. Schema Validation (Missing: {missing_tables})")

    db: Session = SessionLocal()
    try:
        # Test 3: Foreign Key & Relationships Test
        chunks_with_doc = db.query(KnowledgeChunk).join(Document).count()
        total_chunks_db = db.query(KnowledgeChunk).count()
        if chunks_with_doc == total_chunks_db and total_chunks_db > 0:
            test_results["Foreign Key integrity"] = "PASS"
            print(f"[PASS] 3. Foreign Key Integrity ({chunks_with_doc}/{total_chunks_db} chunks linked to documents)")
        else:
            test_results["Foreign Key integrity"] = f"FAIL ({chunks_with_doc}/{total_chunks_db})"
            print(f"[FAIL] 3. Foreign Key Integrity ({chunks_with_doc}/{total_chunks_db})")

        # Test 4: Unique Constraints Test
        unique_ids_count = db.query(KnowledgeChunk.chunk_id).distinct().count()
        if unique_ids_count == total_chunks_db:
            test_results["Unique constraint test"] = "PASS"
            print(f"[PASS] 4. Unique Constraint Test ({unique_ids_count}/{total_chunks_db} distinct chunk_ids)")
        else:
            test_results["Unique constraint test"] = "FAIL"
            print(f"[FAIL] 4. Unique Constraint Test ({unique_ids_count}/{total_chunks_db})")

        # Test 5: Knowledge Base 1-to-1 Match Test (JSON vs DB)
        with open(kb_json_path, "r", encoding="utf-8") as f:
            json_chunks = json.load(f)

        json_count = len(json_chunks)
        lost_chunks = 0
        mismatched_content = 0

        for item in json_chunks:
            c_id = item["chunk_id"]
            db_chunk = db.query(KnowledgeChunk).filter_by(chunk_id=c_id).first()
            if not db_chunk:
                lost_chunks += 1
            else:
                if db_chunk.content.strip() != item["content"].strip():
                    mismatched_content += 1

        print("----------------------------------------")
        print(f"JSON Chunks Count : {json_count}")
        print(f"DB Chunks Count   : {total_chunks_db}")
        print(f"Lost Chunks       : {lost_chunks}")
        print(f"Content Mismatches: {mismatched_content}")

        if json_count == total_chunks_db and lost_chunks == 0 and mismatched_content == 0:
            test_results["Knowledge Base Integrity"] = "PASS"
            print(f"[PASS] 5. Knowledge Base Integrity Match (100% {json_count}/{json_count} exact match)")
        else:
            test_results["Knowledge Base Integrity"] = f"FAIL (Lost: {lost_chunks}, Mismatch: {mismatched_content})"
            print(f"[FAIL] 5. Knowledge Base Integrity Match")

        # Summary
        print("========================================")
        print("SUMMARY TEST RESULTS")
        print("========================================")
        all_passed = True
        for k, v in test_results.items():
            print(f" - {k}: {v}")
            if "PASS" not in v:
                all_passed = False

        print("----------------------------------------")
        if all_passed:
            print("FINAL VERIFICATION: PASS")
        else:
            print("FINAL VERIFICATION: FAIL")
        print("========================================")
        return all_passed

    finally:
        db.close()

if __name__ == "__main__":
    success = run_database_tests()
    if not success:
        sys.exit(1)
