import re
from typing import List, Dict, Any

class DocumentChunker:
    """
    Trình phân rã tài liệu phân cấp (Hierarchical Parent-Child Chunking) 
    kết hợp Bơm Ngữ cảnh (Context Injection) cho hệ thống vnxBox Enterprise.
    """
    
    def __init__(self, max_child_words: int = 400, overlap_words: int = 50):
        self.max_child_words = max_child_words
        self.overlap_words = overlap_words

    def clean_title(self, raw_title: str) -> str:
        """
        Làm sạch tiêu đề bằng Regex: Loại bỏ hiện tượng lặp từ vô nghĩa 
        (Ví dụ: 'Phần 1: Phần 1: Giới thiệu' -> 'Phần 1: Giới thiệu').
        """
        if not raw_title:
            return "Chương chưa đặt tên"
        
        # Regex tìm các cụm từ lặp dạng "Word: Word:" hoặc "Phần X: Phần X:"
        cleaned = re.sub(r'\b(Phần|Chương|Điều|Mục)\s+(\d+)(?:\s*[:\-–]\s*\1\s+\2)+', r'\1 \2', raw_title, flags=re.IGNORECASE)
        # Loại bỏ các từ lặp đơn lẻ liền kề (ví dụ: "Quy định Quy định")
        cleaned = re.sub(r'\b(\w+)(\s+\1)+\b', r'\1', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def generate_context_prefix(self, domain_name: str, sub_domain: str, source_file: str, sheet_name: str, location_code: str) -> str:
        """
        Tạo khối Context Header chuẩn ép cứng vào đầu mỗi chunk theo đúng chuẩn Master vnxBox.
        """
        header = f"""==================================================
CONTEXT HEADER:
- DOMAIN: {domain_name}
- SUB_DOMAIN: {sub_domain if sub_domain else "Chung"}
- SOURCE_FILE: {source_file if source_file else "Tài liệu hệ thống"}"""
        if sheet_name:
            header += f" | SHEET: {sheet_name}"
        header += f"\n- LOCATION: {location_code}\n==================================================\n"
        return header

    def split_into_child_chunks(self, text: str) -> List[str]:
        """
        Cắt tài liệu thành các Child Chunks (300-500 từ) có độ chồng lấp (overlap) 
        để bảo toàn mạch ý nghĩa ngữ nghĩa.
        """
        words = text.split()
        if len(words) <= self.max_child_words:
            return [text]

        chunks = []
        start = 0
        while start < len(words):
            end = start + self.max_child_words
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            # Dịch chuyển con trỏ có tính toán overlap
            start += (self.max_child_words - self.overlap_words)
            
        return chunks

    def process_document(self, parent_id: str, title: str, domain_name: str, sub_domain: str, source_file: str, sheet_name: str, location_code: str, full_content: str) -> Dict[str, Any]:
        """
        Xử lý toàn bộ tài liệu thô/Chapter: Băm thành các Child Chunks có gắn Header ngữ cảnh sâu.
        """
        clean_doc_title = self.clean_title(title)
        context_prefix = self.generate_context_prefix(domain_name, sub_domain, source_file, sheet_name, location_code)
        
        raw_child_texts = self.split_into_child_chunks(full_content)
        child_chunks = []
        
        for idx, raw_text in enumerate(raw_child_texts):
            # Ép cứng Context Header vào từng Child Chunk
            injected_content = context_prefix + raw_text
            child_chunks.append({
                "chunk_index": idx + 1,
                "parent_id": parent_id,
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
            "domain_name": domain_name,
            "sub_domain": sub_domain,
            "source_file": source_file,
            "sheet_name": sheet_name,
            "total_children": len(child_chunks),
            "parent_content": full_content,
            "child_chunks": child_chunks
        }