import json
import sys
from pathlib import Path

DEFAULT_KB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'knowledge_base.json'

def validate_kb(filepath=DEFAULT_KB_PATH):
    print('========================================')
    print('KNOWLEDGE BASE VALIDATION')
    print('========================================')
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f'STATUS: FAIL - Could not parse JSON: {e}')
        return False

    total_chunks = len(data)
    chunk_ids = [item.get('chunk_id') for item in data]
    unique_ids = set(chunk_ids)
    duplicate_ids = total_chunks - len(unique_ids)
    
    empty_content = 0
    missing_source = 0
    missing_title = 0
    invalid_schema = 0
    exact_duplicate_content = 0
    
    required_fields = ['chunk_id', 'title', 'content', 'source', 'source_type', 'category', 'language', 'metadata']
    
    seen_contents = set()
    external_missing_license = 0
    
    for idx, item in enumerate(data):
        for field in required_fields:
            if field not in item:
                invalid_schema += 1
                print(f'Chunk {idx} ({item.get("chunk_id")}) missing required field: {field}')
                break
                
        content = item.get('content', '').strip()
        if not content:
            empty_content += 1
            
        title = item.get('title', '').strip()
        if not title:
            missing_title += 1
            
        source = item.get('source', '').strip()
        if not source:
            missing_source += 1
            
        # Chunk từ nguồn ngoài (scientific_reference) phải có giấy phép, URL và trích nguyên văn để kiểm chứng
        if item.get('source_type') == 'scientific_reference':
            meta = item.get('metadata') or {}
            if not (meta.get('license') and meta.get('url') and meta.get('original_quote')):
                external_missing_license += 1
                print(f'Chunk {item.get("chunk_id")} thiếu license/url/original_quote')

        if content in seen_contents:
            exact_duplicate_content += 1
        else:
            seen_contents.add(content)

    print(f'Total chunks: {total_chunks}')
    print(f'Unique IDs: {len(unique_ids)}')
    print(f'Duplicate IDs: {duplicate_ids}')
    print(f'Empty content: {empty_content}')
    print(f'Missing title: {missing_title}')
    print(f'Missing source: {missing_source}')
    print(f'Invalid JSON records: 0')
    print(f'Schema violations: {invalid_schema}')
    print(f'Exact duplicate content: {exact_duplicate_content}')
    print(f'External chunks missing license/url/quote: {external_missing_license}')

    passed = (
        total_chunks >= 162 and
        external_missing_license == 0 and
        duplicate_ids == 0 and
        empty_content == 0 and
        missing_title == 0 and
        missing_source == 0 and
        invalid_schema == 0 and
        exact_duplicate_content == 0
    )

    print('----------------------------------------')
    if passed:
        print('STATUS: PASS')
    else:
        print('STATUS: FAIL')
    print('========================================')
    return passed

if __name__ == '__main__':
    success = validate_kb()
    if not success:
        sys.exit(1)
