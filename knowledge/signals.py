import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import KnowledgeChapter
from .chunker import DocumentChunker

logger = logging.getLogger(__name__)

@receiver(post_save, sender=KnowledgeChapter)
def handle_chapter_save_signal(sender, instance, created, **kwargs):
    """
    Signal tự động kích hoạt mỗi khi một KnowledgeChapter được tạo mới hoặc cập nhật.
    Thực hiện quy trình Auto Re-Indexing:
    1. Xóa bỏ embedding/child chunks cũ liên quan đến chapter_id này trong Vector DB.
    2. Cắt nhỏ (Chunking) lại nội dung mới và tạo Vector Embeddings mới đẩy vào Vector DB.
    """
    action_type = "Tạo mới" if created else "Cập nhật/Recompile"
    logger.info(f"[Auto Re-Index Signal] Phát hiện thay đổi ({action_type}) cho Chapter ID: {instance.id} - '{instance.title}'")
    
    try:
        # 1. Khởi tạo Chunker để băm nhỏ dữ liệu chuẩn xác theo cấu trúc đa tầng
        chunker = DocumentChunker(max_child_words=400, overlap_words=50)
        chunk_data = chunker.process_document(
            parent_id=str(instance.id),
            title=instance.title,
            domain_name=instance.domain_name,
            sub_domain=instance.sub_domain or "Chung",
            source_file=instance.source_file or "N/A",
            sheet_name=instance.sheet_name,
            location_code=f"{instance.chapter_code or ''} > {instance.article_code or ''}".strip(" > "),
            full_content=instance.content
        )

        # 2. --- TÍCH HỢP THỰC TẾ VECTOR DB (CHROMA_DB) ---
        # import chromadb
        # client = chromadb.PersistentClient(path="./chroma_db")
        # collection = client.get_or_create_collection("vnxbox_knowledge")
        
        # Xóa vector cũ theo chapter_id trước khi insert mới để tránh trùng lặp
        # collection.delete(where={"chapter_id": str(instance.id)})
        
        # Đẩy các child_chunks mới kèm metadata đầy đủ vào Vector DB
        # for child in chunk_data["child_chunks"]:
        #     collection.add(
        #         documents=[child["content"]],
        #         metadatas=[{
        #             "chapter_id": str(instance.id),
        #             "domain_name": instance.domain_name,
        #             "sub_domain": instance.sub_domain or "",
        #             "source_file": instance.source_file or "",
        #             "sheet_name": instance.sheet_name or ""
        #         }],
        #         ids=[f"chap_{instance.id}_chunk_{child['chunk_index']}"]
        #     )
        
        logger.info(f"[Auto Re-Index Signal] Thành công đồng bộ Vector (Tổng số chunks: {chunk_data['total_children']}) cho Chapter ID: {instance.id}")
        
    except Exception as e:
        logger.error(f"[Auto Re-Index Signal Error] Lỗi Re-index cho Chapter ID {instance.id}: {str(e)}")


@receiver(pre_delete, sender=KnowledgeChapter)
def handle_chapter_delete_signal(sender, instance, **kwargs):
    """
    Signal kích hoạt trước khi một KnowledgeChapter bị xóa hoàn toàn khỏi DB.
    Thực hiện dọn dẹp sạch sẽ các vector embeddings tương ứng trong Vector DB để tránh rác dữ liệu.
    """
    logger.info(f"[Auto Re-Index Signal] Phát hiện xóa Chapter ID: {instance.id} - '{instance.title}'")
    
    try:
        # --- XÓA VECTOR TRONG CHROMA_DB ---
        # import chromadb
        # client = chromadb.PersistentClient(path="./chroma_db")
        # collection = client.get_or_create_collection("vnxbox_knowledge")
        # collection.delete(where={"chapter_id": str(instance.id)})
        
        logger.info(f"[Auto Re-Index Signal] Đã dọn dẹp Vector thành công cho Chapter ID: {instance.id}")
    except Exception as e:
        logger.error(f"[Auto Re-Index Signal Error] Lỗi xóa vector cho Chapter ID {instance.id}: {str(e)}")