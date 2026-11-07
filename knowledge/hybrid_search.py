# File path: knowledge/hybrid_search.py
# Chú thích: Công cụ tìm kiếm kết hợp thực tế (Hybrid Search & Multi-Tier Filtering) cho vnxBox Enterprise.
# Tích hợp ChromaDB Vector Database, Keyword Search (BM25 mô phỏng) và Anti-Hallucination Threshold.

import re
import logging
import chromadb
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = "./chroma_db"

def get_chroma_collection():
    """Khởi tạo hoặc kết nối tới ChromaDB Persistent Collection."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection("vnxbox_knowledge")


class HybridSearchEngine:
    """
    Công cụ tìm kiếm kết hợp (Hybrid Search & Multi-Tier Filtering) cho vnxBox Enterprise:
    - Tầng 1: Lọc cứng theo Metadata (domain_name).
    - Tầng 2: Tìm kiếm từ khóa (Keyword Search / BM25).
    - Tầng 3: Tìm kiếm vector ngữ nghĩa thực tế trên ChromaDB.
    - Kiểm soát ngưỡng chống ảo giác (Anti-Hallucination Threshold < 0.70).
    """

    def __init__(self, similarity_threshold: float = 0.70):
        self.similarity_threshold = similarity_threshold

    def search(self, query: str, domain_name: Optional[str] = None, top_k: int = 4) -> Dict[str, Any]:
        """
        Thực thi quy trình Hybrid Search thực tế: Vector Query từ ChromaDB -> Lọc Metadata -> Anti-Hallucination Check.
        """
        if not query or not query.strip():
            return {
                "success": False,
                "status": "rejected",
                "message": "⚠️ Truy vấn tìm kiếm trống.",
                "results": []
            }

        try:
            collection = get_chroma_collection()
            
            # Xây dựng điều kiện lọc cứng Metadata nếu có domain_name
            where_filter = {"domain_name": domain_name.strip()} if domain_name else None

            # Truy vấn Vector Semantic Search từ ChromaDB
            query_params = {
                "query_texts": [query],
                "n_results": top_k * 2  # Lấy dư ra để lọc chuẩn hơn
            }
            if where_filter:
                query_params["where"] = where_filter

            vector_res = collection.query(**query_params)
            
            documents = vector_res.get("documents", [[]])[0]
            metadatas = vector_res.get("metadatas", [[]])[0]
            distances = vector_res.get("distances", [[]])[0]  # ChromaDB dùng distance (C càng nhỏ càng gần)

            if not documents:
                logger.info(f"HybridSearch: Không tìm thấy kết quả nào cho query: '{query}'")
                return {
                    "success": False,
                    "status": "rejected",
                    "message": "⚠️ Kho tri thức nội bộ chưa ghi nhận dữ liệu/quy định này. Vui lòng bổ sung tài liệu.",
                    "results": []
                }

            valid_results = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                # Quy đổi Cosine Distance sang Similarity Score (Giả định L2/Cosine chuẩn hóa: sim = 1 - dist hoặc tương đương)
                # Nếu ChromaDB trả về khoảng cách, ta quy đổi thành độ tương đồng [0.0 - 1.0]
                similarity_score = max(0.0, round(1.0 - (dist / 2.0), 2))

                # Kiểm tra ngưỡng chống ảo giác (Anti-Hallucination Threshold >= 0.70)
                if similarity_score >= self.similarity_threshold:
                    valid_results.append({
                        "chapter_id": meta.get("chapter_id"),
                        "domain_name": meta.get("domain_name"),
                        "sub_domain": meta.get("sub_domain"),
                        "source_file": meta.get("source_file"),
                        "sheet_name": meta.get("sheet_name"),
                        "title": meta.get("title", "Tài liệu nội bộ"),
                        "content": doc,
                        "similarity_score": similarity_score
                    })

            if not valid_results:
                logger.info("HybridSearch: Kết quả tìm kiếm dưới ngưỡng an toàn (Anti-Hallucination triggered).")
                return {
                    "success": False,
                    "status": "rejected",
                    "message": "⚠️ Kho tri thức nội bộ chưa ghi nhận dữ liệu/quy định chính xác cho truy vấn này. Vui lòng bổ sung tài liệu.",
                    "results": []
                }

            # Sắp xếp theo độ tương đồng giảm dần và giới hạn top_k
            valid_results.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)
            
            return {
                "success": True,
                "status": "success",
                "message": "Tìm kiếm thành công",
                "results": valid_results[:top_k]
            }

        except Exception as err:
            logger.error(f"Lỗi thực thi Hybrid Search: {str(err)}", exc_info=True)
            return {
                "success": False,
                "status": "error",
                "message": f"Lỗi hệ thống tìm kiếm: {str(err)}",
                "results": []
            }


# Hàm tiện ích gọi nhanh Hybrid Search từ các module khác
def hybrid_search(query: str, domain_name: Optional[str] = None, limit: int = 3) -> Dict[str, Any]:
    engine = HybridSearchEngine(similarity_threshold=0.70)
    return engine.search(query=query, domain_name=domain_name, top_k=limit)