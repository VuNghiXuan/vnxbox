# File path: knowledge/signals.py
# Chú thích: Django Signals tự động xử lý Auto Re-Indexing & Vector Cleanup 
# mỗi khi KnowledgeChapter được Tạo mới, Cập nhật (Recompile) hoặc Xóa khỏi cơ sở dữ liệu.
# Đã tích hợp hỗ trợ đa công ty (company_code) và tự sinh nhân sự qua DynamicAgentFactory.

import logging
import chromadb
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import KnowledgeChapter
from .chunker import DocumentChunker
from .agents.agent_factory import DynamicAgentFactory

logger = logging.getLogger(__name__)

# Khởi tạo ChromaDB Persistent Client chạy offline trong thư mục local
CHROMA_DB_PATH = "./chroma_db"

def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection("vnxbox_knowledge")


@receiver(post_save, sender=KnowledgeChapter)
def handle_chapter_save_signal(sender, instance, created, **kwargs):
    """
    Signal tự động kích hoạt mỗi khi một KnowledgeChapter được tạo mới hoặc cập nhật.
    Thực hiện quy trình Auto Re-Indexing:
    1. Xóa bỏ embedding/child chunks cũ liên quan đến chapter_id này trong Vector DB.
    2. Cắt nhỏ (Chunking) lại nội dung mới và tạo Vector Embeddings mới đẩy vào Vector DB.
    3. Tự động bảo đảm nhân viên chuyên trách (Agent) sẵn sàng qua DynamicAgentFactory.
    """
    action_type = "Tạo mới" if created else "Cập nhật/Recompile"
    logger.info(f"[Auto Re-Index Signal] Phát hiện thay đổi ({action_type}) cho Chapter ID: {instance.id} - '{instance.title}'")
    
    try:
        # Lấy mã công ty chủ quản từ quan hệ ForeignKey
        comp_code = instance.company.company_code if instance.company else "GENERAL"
        comp_name = instance.company.company_name if instance.company else "Tập đoàn vnxBox"

        # 1. Khởi tạo Chunker để băm nhỏ dữ liệu chuẩn xác theo cấu trúc đa tầng
        chunker = DocumentChunker()
        chunk_data = chunker.process_document(
            parent_id=str(instance.id),
            title=instance.title,
            domain_name=instance.domain_name,
            sub_domain=instance.sub_domain or "Chung",
            source_file=instance.source_file or "N/A",
            sheet_name=instance.sheet_name or "",
            location_code=f"{instance.chapter_code or ''} {instance.article_code or ''}".strip(" > "),
            full_content=instance.content,
            company_code=comp_code
        )

        # 2. Đồng bộ Vector DB (ChromaDB)
        collection = get_chroma_collection()
        
        # Xóa vector cũ theo chapter_id trước khi insert mới để tránh trùng lặp
        collection.delete(where={"chapter_id": str(instance.id)})
        
        # Đẩy các child_chunks mới kèm metadata đầy đủ vào Vector DB
        for child in chunk_data["child_chunks"]:
            collection.add(
                documents=[child["content"]],
                metadatas=[{
                    "chapter_id": str(instance.id),
                    "company_code": comp_code,
                    "domain_name": instance.domain_name,
                    "sub_domain": instance.sub_domain or "",
                    "source_file": instance.source_file or "",
                    "sheet_name": instance.sheet_name or ""
                }],
                ids=[f"chap_{instance.id}_chunk_{child['chunk_index']}"]
            )
        
        logger.info(f"[Auto Re-Index Signal] Thành công đồng bộ Vector (Tổng số chunks: {chunk_data['total_children']}) cho Chapter ID: {instance.id}")

        # 3. Kích hoạt tự động Dynamic Agent Factory để chuẩn bị nhân sự chuyên trách
        DynamicAgentFactory.spawn_or_get_specialist(
            company_code=comp_code,
            company_name=comp_name,
            sub_field=instance.sub_domain or instance.domain_name,
            sample_snippet=instance.content[:300]
        )
        
    except Exception as e:
        logger.error(f"[Auto Re-Index Signal Error] Lỗi Re-index cho Chapter ID {instance.id}: {str(e)}", exc_info=True)


@receiver(pre_delete, sender=KnowledgeChapter)
def handle_chapter_delete_signal(sender, instance, **kwargs):
    """
    Signal kích hoạt trước khi một KnowledgeChapter bị xóa hoàn toàn khỏi DB.
    Thực hiện dọn dẹp sạch sẽ các vector embeddings tương ứng trong Vector DB để tránh rác dữ liệu.
    """
    logger.info(f"[Auto Re-Index Signal] Phát hiện xóa Chapter ID: {instance.id} - '{instance.title}'")
    
    try:
        collection = get_chroma_collection()
        collection.delete(where={"chapter_id": str(instance.id)})
        
        logger.info(f"[Auto Re-Index Signal] Đã dọn dẹp Vector thành công cho Chapter ID: {instance.id}")
    except Exception as e:
        logger.error(f"[Auto Re-Index Signal Error] Lỗi xóa vector cho Chapter ID {instance.id}: {str(e)}", exc_info=True)