# File path: knowledge/hybrid_search.py
# Chú thích: Công cụ tìm kiếm kết hợp thực tế (Hybrid Search & Multi-Tier Filtering) cho vnxBox Enterprise.
# Tích hợp ChromaDB Vector Database, lọc Metadata theo Company / Domain và Anti-Hallucination Threshold.

import logging
import chromadb
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = "./chroma_db"

def get_chroma_collection():
    """Khởi tạo hoặc kết nối tới ChromaDB Persistent Collection."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection("vnxbox_knowledge")


class HybridSearchEngine:
    """
    Công cụ tìm kiếm kết hợp (Hybrid Search & Multi-Tier Filtering) cho vnxBox Enterprise:
    - Tầng 1: Lọc cứng theo Metadata (company_code, domain_name).
    - Tầng 2: Tìm kiếm vector ngữ nghĩa thực tế trên ChromaDB.
    - Tầng 3: Kiểm soát ngưỡng chống ảo giác (Anti-Hallucination Threshold < 0.70).
    """

    def __init__(self, similarity_threshold: float = 0.70):
        self.similarity_threshold = similarity_threshold

    def search(self, query: str, company_code: Optional[str] = None, domain_name: Optional[str] = None, top_k: int = 4) -> Dict[str, Any]:
        """
        Thực thi quy trình Hybrid Search: Vector Query từ ChromaDB -> Lọc Metadata đa tầng -> Anti-Hallucination Check.
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
            
            # Xây dựng điều kiện lọc cứng Metadata linh hoạt theo Company và Domain
            filter_conditions = []
            if company_code and company_code.strip() != "GENERAL":
                filter_conditions.append({"company_code": company_code.strip().upper()})
            if domain_name and domain_name.strip():
                filter_conditions.append({"domain_name": domain_name.strip()})

            where_filter = None
            if len(filter_conditions) == 1:
                where_filter = filter_conditions[0]
            elif len(filter_conditions) > 1:
                where_filter = {"$and": filter_conditions}

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
            distances = vector_res.get("distances", [[]])[0]

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
                # Quy đổi khoảng cách sang Similarity Score [0.0 - 1.0]
                similarity_score = max(0.0, round(1.0 - (dist / 2.0), 2))

                # Kiểm tra ngưỡng chống ảo giác (Anti-Hallucination Threshold >= 0.70)
                if similarity_score >= self.similarity_threshold:
                    valid_results.append({
                        "chapter_id": meta.get("chapter_id"),
                        "company_code": meta.get("company_code"),
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
def hybrid_search(query: str, company_code: Optional[str] = None, domain_name: Optional[str] = None, limit: int = 3) -> Dict[str, Any]:
    engine = HybridSearchEngine(similarity_threshold=0.70)
    return engine.search(query=query, company_code=company_code, domain_name=domain_name, top_k=limit)