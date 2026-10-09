import json
import os
import re
from pathlib import Path

# Gốc dự án (thư mục cha của scripts/), để chạy được từ bất kỳ thư mục làm việc nào
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / 'data' / 'raw'
EXTERNAL_DIR = ROOT / 'data' / 'external'
OUTPUT_PATH = ROOT / 'data' / 'knowledge_base.json'

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

c0 = load_json(RAW_DIR / 'tl1_chunks.json')
c1 = load_json(RAW_DIR / 'tealeafdiseasebd_chunks.json')
c2 = load_json(RAW_DIR / 'laichau_chunks.json')

standardized_chunks = []
global_counter = 1

# Process data/raw/tl1_chunks.json (TL1)
for item in c0:
    chunk_id = f'tea_{global_counter:06d}'
    global_counter += 1
    
    title = item.get('title', '').strip()
    content = item.get('content', '').strip()
    orig_id = item.get('chunk_id', '')
    
    # Infer disease if clearly mentioned in title or text
    disease = ''
    txt_lower = (title + ' ' + content).lower()
    if 'bệnh' in txt_lower or 'rệp' in txt_lower or 'bọ trĩ' in txt_lower or 'nhện đỏ' in txt_lower:
        # Check specific disease names
        diseases = ['bệnh thối búp', 'bệnh đốm nâu', 'bệnh chấm xám', 'bệnh chổi rồng', 'bệnh sương muối', 'rệp xanh', 'bọ trĩ', 'nhện đỏ', 'bọ xít muỗi']
        found = [d for d in diseases if d in txt_lower]
        if found:
            disease = ', '.join(found)
            
    category = ''
    if any(k in txt_lower for k in ['sâu', 'bệnh', 'rệp', 'bọ', 'nhện']):
        category = 'pest_and_disease'
    elif any(k in txt_lower for k in ['trồng', 'bón phân', 'đốn', 'làm đất', 'giống', 'tạo tán', 'hái', 'thu hoạch']):
        category = 'cultivation_technique'
    elif 'đất' in txt_lower or 'vùng' in txt_lower or 'khí hậu' in txt_lower:
        category = 'ecological_conditions'
    else:
        category = 'general_knowledge'

    chunk = {
        'chunk_id': chunk_id,
        'title': title,
        'content': content,
        'source': 'Tài liệu kỹ thuật trồng và chăm sóc chè (TL1)',
        'source_type': 'technical_document',
        'category': category,
        'topic': title,
        'disease': disease,
        'dataset': 'TL1_Tea_Technical_Guideline',
        'version': '1.0',
        'language': 'vi',
        'metadata': {
            'document': 'Tài liệu kỹ thuật trồng và chăm sóc chè (TL1)',
            'section': title,
            'page': None,
            'region': 'Việt Nam',
            'year': None,
            'original_chunk_id': orig_id
        }
    }
    standardized_chunks.append(chunk)

# Process data/raw/tealeafdiseasebd_chunks.json (TeaLeafDiseaseBD)
for item in c1:
    chunk_id = f'tea_{global_counter:06d}'
    global_counter += 1
    
    title = item.get('title', '').strip()
    content = (item.get('content') or item.get('text') or '').strip()
    orig_id = item.get('chunk_id', '')
    
    meta_in = item.get('metadata', {})
    
    chunk = {
        'chunk_id': chunk_id,
        'title': title,
        'content': content,
        'source': item.get('source', 'TeaLeafDiseaseBD Documentation'),
        'source_type': item.get('source_type', 'dataset_documentation'),
        'category': item.get('category', 'dataset_overview'),
        'topic': title,
        'disease': item.get('disease') or '',
        'dataset': item.get('dataset', 'TeaLeafDiseaseBD'),
        'version': str(item.get('version', '2')),
        'language': item.get('language', 'vi'),
        'metadata': {
            'document': 'TeaLeafDiseaseBD: Annotated smartphone images and lesion-level labels of tea leaf diseases from Bangladesh',
            'section': item.get('category', ''),
            'page': None,
            'region': 'Bangladesh',
            'year': 2025,
            'doi': meta_in.get('doi'),
            'published': meta_in.get('published'),
            'image_count': meta_in.get('image_count'),
            'original_chunk_id': orig_id
        }
    }
    standardized_chunks.append(chunk)

# Process data/raw/laichau_chunks.json (Lai Chau Technical Guideline)
for item in c2:
    chunk_id = f'tea_{global_counter:06d}'
    global_counter += 1
    
    title = item.get('title', '').strip()
    content = (item.get('content') or item.get('text') or '').strip()
    orig_id = item.get('chunk_id', '')
    
    meta_in = item.get('metadata', {})
    page_val = meta_in.get('page') if isinstance(meta_in, dict) else None
    
    chunk = {
        'chunk_id': chunk_id,
        'title': title,
        'content': content,
        'source': item.get('source', 'Quyết định 450/QĐ-SNNMT Lai Châu 2025'),
        'source_type': 'official_technical_document',
        'category': item.get('category', 'cultivation_technique'),
        'topic': title,
        'disease': item.get('disease') or '',
        'dataset': item.get('dataset', 'LaiChau_Tea_Technical_Guideline'),
        'version': str(item.get('version', '2025')),
        'language': item.get('language', 'vi'),
        'metadata': {
            'document': 'Quyết định 450/QĐ-SNNMT Lai Châu 2025',
            'section': meta_in.get('section', '') if isinstance(meta_in, dict) else '',
            'page': page_val,
            'pages': meta_in.get('pages') if isinstance(meta_in, dict) else None,
            'region': 'Lai Châu',
            'year': 2025,
            'original_chunk_id': orig_id
        }
    }
    standardized_chunks.append(chunk)

# Nguồn tri thức bên ngoài (tài liệu khoa học, cơ sở dữ liệu mở) trong data/external/*.json.
# Được nối SAU 162 đoạn gốc để các chunk_id cũ không đổi; thứ tự tệp cố định (sắp theo tên) để ID ổn định.
for ext_file in sorted(EXTERNAL_DIR.glob('*.json')):
    ext = load_json(ext_file)
    doc = ext['document']
    for local_index, item in enumerate(ext['chunks'], 1):
        chunk_id = f'tea_{global_counter:06d}'
        global_counter += 1
        meta_in = item.get('metadata', {})
        standardized_chunks.append({
            'chunk_id': chunk_id,
            'title': item['title'].strip(),
            'content': item['content'].strip(),
            'source': doc['source'],
            'source_type': doc['source_type'],
            'category': item['category'],
            'topic': item['title'].strip(),
            'disease': item.get('disease') or '',
            'dataset': ext['dataset'],
            'version': str(doc['version']),
            'language': 'vi',
            'metadata': {
                'document': doc['title'],
                'section': meta_in.get('section', ''),
                'page': meta_in.get('page'),
                'region': meta_in.get('region', doc.get('region', '')),
                'year': meta_in.get('year', doc.get('year')),
                'url': doc.get('url'),
                'license': doc.get('license'),
                'original_quote': meta_in.get('original_quote'),
                'original_chunk_id': f"{ext['dataset']}_{local_index:03d}",
            },
        })

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(standardized_chunks, f, ensure_ascii=False, indent=2)

print(f'Successfully generated {OUTPUT_PATH.relative_to(ROOT)} with {len(standardized_chunks)} items.')
