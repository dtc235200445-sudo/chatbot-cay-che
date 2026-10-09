from typing import List, Dict, Any

class ContextBuilder:
    @staticmethod
    def build_context(retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Format top-k retrieved chunks into a structured RAG context block."""
        if not retrieved_chunks:
            return "Không tìm thấy tri thức liên quan trong Kho dữ liệu Cây chè."
            
        context_parts = []
        for idx, item in enumerate(retrieved_chunks, 1):
            chunk_id = item.get("chunk_id", f"chunk_{idx}")
            meta = item.get("metadata", {})
            title = meta.get("title") or item.get("title") or "Tri thức Cây chè"
            source = meta.get("source") or item.get("source") or "Tài liệu kỹ thuật"
            section = meta.get("section") or ""
            page = meta.get("page")
            
            source_info = f"{source}"
            if section:
                source_info += f" - Mục: {section}"
            if page:
                source_info += f" (Trang {page})"
                
            content = item.get("content", "").strip()
            score = item.get("similarity_score", 0.0)
            
            block = (
                f"[Nguồn {idx} | ID: {chunk_id} | Trích từ: {source_info} | Độ khớp: {score:.2f}]\n"
                f"Tiêu đề: {title}\n"
                f"Nội dung: {content}"
            )
            context_parts.append(block)
            
        return "\n\n---\n\n".join(context_parts)

    @staticmethod
    def extract_sources(retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract structured list of citations from retrieved chunks."""
        sources = []
        seen = set()
        
        for item in retrieved_chunks:
            cid = item.get("chunk_id")
            if cid in seen:
                continue
            seen.add(cid)
            
            meta = item.get("metadata", {})
            sources.append({
                "chunk_id": cid,
                "title": meta.get("title") or item.get("title", ""),
                "source": meta.get("source") or item.get("source", ""),
                "section": meta.get("section") or "",
                "page": meta.get("page"),
                "similarity_score": item.get("similarity_score", 0.0)
            })
            
        return sources
