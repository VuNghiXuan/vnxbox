# File path: knowledge/chunker.py
# Chú thích: Trình phân rã tài liệu phân cấp (Hierarchical Parent-Child Chunking) 
# kết hợp Bơm Ngữ cảnh (Context Injection) & Hardware Adaptive Chunking cho vnxBox Enterprise.

import re
from typing import List, Dict, Any
from .ai_services import profile_client_hardware

def get_hardware_adaptive_chunk_config() -> Dict[str, Any]:
    """Tự động tính toán kích thước Chunk dựa trên phần cứng máy tính."""
    hw = profile_client_hardware()
    tier = hw.get("tier", "Mid-Range")
    
    if tier == "High-End":
        return {"chunk_size": 600, "chunk_overlap": 100, "profile_tier": tier}
    elif tier == "Low-End":
        return {"chunk_size": 250, "chunk_overlap": 40, "profile_tier": tier}
    else:
        return {"chunk_size": 400, "chunk_overlap": 60, "profile_tier": tier}


class DocumentChunker:
    """
    Trình phân rã tài liệu phân cấp (Hierarchical Parent-Child Chunking) 
    kết hợp Bơm Ngữ cảnh (Context Injection) tự động linh hoạt theo cấu hình phần cứng máy khách.
    """
    
    def __init__(self, max_child_words: int = None, overlap_words: int = None):
        # Tự động lấy cấu hình băm Chunk theo sức mạnh phần cứng máy tính (RAM/CPU/GPU)
        hw_chunk_config = get_hardware_adaptive_chunk_config()
        
        self.max_child_words = max_child_words if max_child_words else hw_chunk_config["chunk_size"]
        self.overlap_words = overlap_words if overlap_words is not None else hw_chunk_config["chunk_overlap"]
        self.profile_tier = hw_chunk_config.get("profile_tier", "Mid-Range")

    def clean_title(self, raw_title: str) -> str:
        """
        Làm sạch tiêu đề bằng Regex: Loại bỏ hiện tượng lặp từ vô nghĩa 
        (Ví dụ: 'Phần 1: Phần 1: Giới thiệu' -> 'Phần 1: Giới thiệu').
        """
        if not raw_title:
            return "Chương chưa đặt tên"
        
        cleaned = re.sub(
            r'\b(Phần|Chương|Điều|Mục)\s+(\d+)(?:\s*[:\-–]\s*\1\s+\2)+', 
            r'\1 \2', 
            raw_title, 
            flags=re.IGNORECASE
        )
        cleaned = re.sub(r'\b(\w+)(\s+\1)+\b', r'\1', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def generate_context_prefix(
        self, 
        company_code: str,
        domain_name: str, 
        sub_domain: str, 
        source_file: str, 
        sheet_name: str, 
        location_code: str
    ) -> str:
        """
        Tạo khối Context Header chuẩn ép cứng vào đầu mỗi chunk theo đúng chuẩn Master vnxBox Enterprise.
        """
        header = (
            "==================================================\n"
            "CONTEXT HEADER:\n"
            f"- COMPANY_CODE: {company_code if company_code else 'GENERAL'}\n"
            f"- DOMAIN: {domain_name}\n"
            f"- SUB_DOMAIN: {sub_domain if sub_domain else 'Chung'}\n"
            f"- SOURCE_FILE: {source_file if source_file else 'Tài liệu hệ thống'}"
        )
        if sheet_name:
            header += f" | SHEET: {sheet_name}"
            
        header += (
            f"\n- LOCATION: {location_code if location_code else 'Chung'}\n"
            "==================================================\n\n"
        )
        return header

    def split_into_child_chunks(self, text: str) -> List[str]:
        """
        Cắt tài liệu thành các Child Chunks có độ chồng lấp (overlap) 
        bảo toàn ranh giới Điều khoản/Bảng biểu trước khi chi tiết hóa theo từ.
        """
        words = text.split()
        if len(words) <= self.max_child_words:
            return [text]

        chunks = []
        start = 0
        step = self.max_child_words - self.overlap_words
        if step <= 0:
            step = self.max_child_words

        while start < len(words):
            end = start + self.max_child_words
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            start += step
            
        return chunks

    def process_document(
        self, 
        parent_id: str, 
        title: str, 
        domain_name: str, 
        sub_domain: str, 
        source_file: str, 
        sheet_name: str, 
        location_code: str, 
        full_content: str,
        company_code: str = "GENERAL"
    ) -> Dict[str, Any]:
        """
        Xử lý toàn bộ tài liệu thô/Chapter: Băm thành các Child Chunks có gắn Header ngữ cảnh sâu.
        """
        clean_doc_title = self.clean_title(title)
        context_prefix = self.generate_context_prefix(
            company_code, domain_name, sub_domain, source_file, sheet_name, location_code
        )
        
        raw_child_texts = self.split_into_child_chunks(full_content)
        child_chunks = []
        
        for idx, raw_text in enumerate(raw_child_texts):
            # Ép cứng Context Header vào từng Child Chunk
            injected_content = context_prefix + raw_text
            child_chunks.append({
                "chunk_index": idx + 1,
                "parent_id": parent_id,
                "company_code": company_code,
                "domain_name": domain_name,
                "sub_domain": sub_domain,
                "source_file": source_file,
                "sheet_name": sheet_name,
                "content": injected_content,
                "raw_text": raw_text,
                "word_count": len(raw_text.split())
            })

        return {
            "parent_id": parent_id,
            "title": clean_doc_title,
            "company_code": company_code,
            "domain_name": domain_name,
            "sub_domain": sub_domain,
            "source_file": source_file,
            "sheet_name": sheet_name,
            "profile_tier": self.profile_tier,
            "total_children": len(child_chunks),
            "parent_content": full_content,
            "child_chunks": child_chunks
        }