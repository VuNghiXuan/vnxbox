from rest_framework import serializers
from .models import KnowledgeChapter, KnowledgeFAQ


class KnowledgeFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeFAQ
        fields = ['id', 'question_variation']


class KnowledgeChapterSerializer(serializers.ModelSerializer):
    """Serializer quản lý toàn diện thông tin KnowledgeChapter, bao gồm cả danh sách FAQ variations."""
    faq_variations = KnowledgeFAQSerializer(many=True, read_only=True)

    class Meta:
        model = KnowledgeChapter
        fields = [
            'id', 
            'title', 
            'source_file', 
            'sheet_name', 
            'domain_name', 
            'sub_domain', 
            'chapter_code', 
            'article_code', 
            'summary', 
            'content', 
            'status', 
            'metadata', 
            'faq_variations', # <-- Khớp chính xác với related_name trong model
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class IngestTextSerializer(serializers.Serializer):
    raw_text = serializers.CharField(required=True, help_text="Nội dung văn bản thô cần bóc tách")
    domain_name = serializers.CharField(required=False, default="Quy định chung", help_text="Phân hệ nghiệp vụ")
    scope = serializers.CharField(required=False, default="Toàn hệ thống", help_text="Phạm vi áp dụng của tri thức")


class ChatQuerySerializer(serializers.Serializer):
    question = serializers.CharField(required=True, help_text="Câu hỏi của người dùng")
    domain_name = serializers.CharField(required=False, allow_null=True, default=None, help_text="Lọc theo phân hệ nếu có")
    session_id = serializers.UUIDField(required=False, allow_null=True, default=None, help_text="Mã phiên chat duy trì lịch sử")