# File path: knowledge/search_engine.py
# Chú thích: Động cơ tìm kiếm kết hợp đa tầng (Multi-Tier Hybrid Search & Intent Routing Engine) 
# cho hệ thống vnxBox Enterprise. Tích hợp FAQ Intent Routing, BM25 Keyword Search, Vector Search thực tế trên ChromaDB 
# kèm bộ lọc đa tầng theo Company Code & Domain Name và cơ chế kiểm soát Anti-Hallucination Threshold (< 0.70).

import logging
import chromadb
from django.db.models import Q
from .models import KnowledgeChapter, KnowledgeFAQ

logger = logging.getLogger(__name__)

# Ngưỡng tối thiểu để chấp nhận kết quả tìm kiếm (Chống ảo giác theo chuẩn vnxBox 2026)
SIMILARITY_THRESHOLD = 0.70
CHROMA_DB_PATH = "./chroma_db"


def get_chroma_collection():
    """Khởi tạo hoặc kết nối tới ChromaDB Persistent Collection."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection("vnxbox_knowledge")


def intent_routing_faq(query_text: str, company_code: str = None, domain_name: str = None, limit: int = 3) -> list:
    """
    Bước 1: Định tuyến Ý định (Intent Routing qua bảng KnowledgeFAQ).
    So khớp câu hỏi của người dùng với các câu hỏi mẫu (FAQ Variations) do AI tự sinh 
    để khoanh vùng chính xác Chapter/Điều khoản cần tra cứu, triệt tiêu nhiễu chéo ngành.
    """
    qs = KnowledgeFAQ.objects.select_related('chapter', 'chapter__company').all()
    
    if company_code and company_code.strip() != "GENERAL":
        qs = qs.filter(chapter__company__company_code__iexact=company_code.strip())
    if domain_name:
        qs = qs.filter(chapter__domain_name__iexact=domain_name.strip())
        
    keywords = query_text.split()
    if not keywords:
        return []

    faq_filter = Q()
    for kw in keywords:
        faq_filter |= Q(question_variation__icontains=kw)
        
    matched_faqs = qs.filter(faq_filter).distinct()[:limit]
    
    routed_chapters = []
    seen_ids = set()
    
    for faq in matched_faqs:
        chap = faq.chapter
        if chap.id not in seen_ids:
            seen_ids.add(chap.id)
            routed_chapters.append({
                "chapter_id": chap.id,
                "title": chap.title,
                "company_code": chap.company.company_code if chap.company else "GENERAL",
                "domain_name": chap.domain_name,
                "sub_domain": chap.sub_domain,
                "chapter_code": chap.chapter_code,
                "article_code": chap.article_code,
                "source_file": chap.source_file,
                "sheet_name": chap.sheet_name,
                "content": chap.content,
                "summary": chap.summary,
                "search_type": "intent_routing_faq",
                "score": 0.95  # Điểm tin cậy cao khi khớp câu hỏi mẫu (FAQ)
            })
            
    return routed_chapters


def keyword_search_bm25(query_text: str, company_code: str = None, domain_name: str = None, limit: int = 5) -> list:
    """
    Bước 2: Tìm kiếm từ khóa truyền thống (Keyword Search / BM25-style qua Django ORM).
    Bắt chính xác mã định mức, số hiệu, tên sản phẩm hoặc từ khóa cụ thể.
    """
    qs = KnowledgeChapter.objects.select_related('company').all()
    
    if company_code and company_code.strip() != "GENERAL":
        qs = qs.filter(company__company_code__iexact=company_code.strip())
    if domain_name:
        qs = qs.filter(domain_name__iexact=domain_name.strip())
        
    keywords = query_text.split()
    if not keywords:
        return []

    query_filter = Q()
    for kw in keywords:
        query_filter |= (
            Q(title__icontains=kw) | 
            Q(content__icontains=kw) | 
            Q(sub_domain__icontains=kw) | 
            Q(source_file__icontains=kw)
        )
    
    results = qs.filter(query_filter).distinct()[:limit]
    
    formatted_results = []
    for item in results:
        formatted_results.append({
            "chapter_id": item.id,
            "title": item.title,
            "company_code": item.company.company_code if item.company else "GENERAL",
            "domain_name": item.domain_name,
            "sub_domain": item.sub_domain,
            "chapter_code": item.chapter_code,
            "article_code": item.article_code,
            "source_file": item.source_file,
            "sheet_name": item.sheet_name,
            "content": item.content,
            "summary": item.summary,
            "search_type": "keyword_bm25",
            "score": 0.85  # Điểm giả lập cho keyword match
        })
        
    return formatted_results


def vector_semantic_search(query_text: str, company_code: str = None, domain_name: str = None, limit: int = 5) -> list:
    """
    Bước 3: Tìm kiếm ngữ nghĩa thực tế (Vector Semantic Search trên ChromaDB).
    Truy vấn trực tiếp tập vector nhúng và lọc theo metadata company_code và domain_name nếu có.
    """
    vector_results = []
    try:
        collection = get_chroma_collection()
        
        # Xây dựng điều kiện lọc cứng Metadata trên ChromaDB
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

        query_params = {
            "query_texts": [query_text],
            "n_results": limit
        }
        if where_filter:
            query_params["where"] = where_filter

        res = collection.query(**query_params)
        documents = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            similarity_score = max(0.0, round(1.0 - (dist / 2.0), 2))
            if similarity_score >= SIMILARITY_THRESHOLD:
                chapter_id = meta.get("chapter_id")
                try:
                    chap = KnowledgeChapter.objects.select_related('company').get(id=chapter_id)
                    vector_results.append({
                        "chapter_id": chap.id,
                        "title": chap.title,
                        "company_code": chap.company.company_code if chap.company else meta.get("company_code", "GENERAL"),
                        "domain_name": chap.domain_name,
                        "sub_domain": chap.sub_domain,
                        "chapter_code": chap.chapter_code,
                        "article_code": chap.article_code,
                        "source_file": chap.source_file,
                        "sheet_name": chap.sheet_name,
                        "content": chap.content,
                        "summary": chap.summary,
                        "search_type": "vector_semantic",
                        "score": similarity_score
                    })
                except KnowledgeChapter.DoesNotExist:
                    continue

    except Exception as e:
        logger.warning(f"Lỗi truy vấn Vector Semantic Search trên ChromaDB: {str(e)}")
        
    return vector_results


def hybrid_search(query_text: str, company_code: str = None, domain_name: str = None, limit: int = 5) -> dict:
    """
    Cỗ máy tìm kiếm kết hợp đa tầng (Multi-Tier Hybrid Search Engine):
    - Bước 1: Intent Routing (Truy vấn qua FAQ Variations để xác định đúng ý định nghiệp vụ).
    - Bước 2: Keyword Search (BM25) & Vector Search thực tế trên ChromaDB (hỗ trợ lọc đa công ty / lĩnh vực).
    - Bước 3: Gộp kết quả, khử trùng lặp và kiểm tra ngưỡng Anti-Hallucination.
    - Bước 4: Trả về danh sách tài liệu chuẩn kèm định vị sâu.
    """
    logger.info(f"[Hybrid Search & Intent Routing] Truy vấn: '{query_text}' | Công ty: {company_code} | Phân hệ: {domain_name}")
    
    # 1. Chạy Intent Routing qua FAQ trước để đón đầu ý định người dùng
    intent_hits = intent_routing_faq(query_text, company_code=company_code, domain_name=domain_name, limit=limit)
    
    # 2. Thu thập kết quả từ Keyword Search (BM25)
    keyword_hits = keyword_search_bm25(query_text, company_code=company_code, domain_name=domain_name, limit=limit)
    
    # 3. Thu thập kết quả từ Vector Semantic Search thực tế
    vector_hits = vector_semantic_search(query_text, company_code=company_code, domain_name=domain_name, limit=limit)
    
    # 4. Gộp và khử trùng lặp (Ưu tiên đưa Intent Routing và Vector hits lên đầu)
    seen_ids = set()
    combined_hits = []
    
    for item in intent_hits + vector_hits + keyword_hits:
        if item["chapter_id"] not in seen_ids:
            seen_ids.add(item["chapter_id"])
            combined_hits.append(item)
            
    # Kiểm tra nếu không tìm thấy bất kỳ tài liệu nào khớp (Áp dụng Anti-Hallucination)
    if not combined_hits:
        logger.info(f"HybridSearch: Không tìm thấy kết quả phù hợp cho truy vấn '{query_text}'. Kích hoạt từ chối.")
        return {
            "success": False,
            "refusal": True,
            "message": "⚠️ Kho tri thức nội bộ chưa ghi nhận dữ liệu/quy định này. Vui lòng bổ sung tài liệu.",
            "results": []
        }
        
    # Giới hạn số lượng kết quả trả về tối đa theo limit
    final_results = combined_hits[:limit]
    
    return {
        "success": True,
        "refusal": False,
        "results": final_results
    }