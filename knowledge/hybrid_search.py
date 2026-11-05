import re
from typing import List, Dict, Any, Optional

class HybridSearchEngine:
    """
    Công cụ tìm kiếm kết hợp (Hybrid Search & Multi-Tier Filtering) cho vnxchat:
    - Tầng 1: Lọc cứng theo Metadata (domain_name).
    - Tầng 2: Tìm kiếm từ khóa (Keyword Search / BM25 mô phỏng hoặc Elasticsearch/SQLite FTS).
    - Tầng 3: Tìm kiếm vector ngữ nghĩa (Vector Semantic Search trên ChromaDB/FAISS).
    """

    def __init__(self, similarity_threshold: float = 0.75):
        """
        similarity_threshold: Ngưỡng kiểm tra độ khớp tối thiểu để phòng chống ảo giác.
        Nếu điểm số thấp hơn ngưỡng này, hệ thống sẽ kích hoạt cơ chế từ chối.
        """
        self.similarity_threshold = similarity_threshold

    def metadata_filter(self, chunks: List[Dict[str, Any]], domain_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Tầng 1: Khóa cứng phạm vi tìm kiếm trong đúng domain_name chuyên ngành, 
        giúp loại bỏ hoàn toàn các phân hệ không liên quan.
        """
        if not domain_name:
            return chunks
        
        filtered = [
            chunk for chunk in chunks 
            if chunk.get("domain_name", "").strip().lower() == domain_name.strip().lower()
        ]
        return filtered

    def keyword_search(self, chunks: List[Dict[str, Any]], query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Tầng 2: Tìm kiếm chính xác từ khóa (Keyword Search) dựa trên tần suất xuất hiện 
        của các từ khóa trong nội dung chunk.
        """
        query_tokens = set(re.findall(r'\w+', query.lower()))
        if not query_tokens:
            return chunks[:top_k]

        scored_chunks = []
        for chunk in chunks:
            content_lower = chunk.get("content", "").lower()
            # Đếm số lượng token khớp trong chunk
            score = sum(1 for token in query_tokens if token in content_lower)
            if score > 0:
                scored_chunk = chunk.copy()
                scored_chunk["keyword_score"] = score
                scored_chunks.append(scored_chunk)

        # Sắp xếp theo điểm từ khóa giảm dần
        scored_chunks.sort(key=lambda x: x.get("keyword_score", 0), reverse=True)
        return scored_chunks[:top_k]

    def vector_semantic_search_mock(self, chunks: List[Dict[str, Any]], query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Tầng 3: Vector Semantic Search (Mô phỏng tích hợp ChromaDB/FAISS trong thực tế).
        Trong code thực tế, đây sẽ là hàm gọi embedding model và tính Cosine Similarity.
        """
        # Giả lập trả về top_k chunks với điểm số similarity ngẫu nhiên từ 0.6 đến 0.95 để test ngưỡng
        results = []
        for idx, chunk in enumerate(chunks[:top_k]):
            sim_score = 0.88 - (idx * 0.05)  # Giả lập điểm giảm dần
            scored_chunk = chunk.copy()
            scored_chunk["similarity_score"] = round(sim_score, 2)
            results.append(scored_chunk)
            
        return results

    def search(self, all_chunks: List[Dict[str, Any]], query: str, domain_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Thực thi quy trình Hybrid Search chuẩn: Metadata Filter -> Keyword/Vector -> Anti-Hallucination Check.
        """
        # Bước 1: Lọc cứng theo phân hệ (Metadata Filtering)
        step1_filtered = self.metadata_filter(all_chunks, domain_name)
        if not step1_filtered:
            return {
                "status": "rejected",
                "message": "Kho tri thức nội bộ chưa ghi nhận dữ liệu hoặc quy định thuộc phân hệ này. Vui lòng bổ sung tài liệu.",
                "results": []
            }

        # Bước 2: Kết hợp Keyword Search & Vector Search
        keyword_results = self.keyword_search(step1_filtered, query, top_k=5)
        vector_results = self.vector_semantic_search_mock(step1_filtered, query, top_k=3)

        # Hợp nhất kết quả và loại bỏ trùng lặp (Dedup)
        seen_ids = set()
        combined_results = []
        for item in vector_results + keyword_results:
            chunk_id = item.get("chunk_index")
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                combined_results.append(item)

        # Bước 3: Kiểm tra Ngưỡng độ khớp (Relevance Threshold & Anti-Hallucination)
        # Lọc ra các kết quả đạt ngưỡng an toàn
        valid_results = [
            res for res in combined_results 
            if res.get("similarity_score", 1.0) >= self.similarity_threshold or "keyword_score" in res
        ]

        if not valid_results:
            return {
                "status": "rejected",
                "message": "Kho tri thức nội bộ chưa ghi nhận dữ liệu/quy định chính xác cho truy vấn này. Vui lòng bổ sung tài liệu.",
                "results": []
            }

        return {
            "status": "success",
            "message": "Tìm kiếm thành công",
            "results": valid_results
        }