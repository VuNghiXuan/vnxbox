# File path: knowledge/serializers.py
# Chú thích: Định nghĩa các Django REST Framework Serializers cho hệ thống vnxBox Enterprise.
# Bao gồm: CompanyDomainSerializer, DepartmentRegistrySerializer, KnowledgeFAQSerializer, 
# KnowledgeChapterSerializer, IngestTextSerializer, ChatQuerySerializer, AuditDebateLogSerializer, 
# QAEvaluationLogSerializer và ChatMessageSerializer.

from rest_framework import serializers
from .models import (
    CompanyDomain, DepartmentRegistry, KnowledgeChapter, 
    KnowledgeFAQ, AuditDebateLog, QAEvaluationLog, ChatMessage
)


class CompanyDomainSerializer(serializers.ModelSerializer):
    """
    Serializer quản lý thông tin các Công ty con / Lĩnh vực nghiệp vụ trong tập đoàn.
    """
    class Meta:
        model = CompanyDomain
        fields = ['id', 'company_code', 'company_name', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class DepartmentRegistrySerializer(serializers.ModelSerializer):
    """
    Serializer quản lý Phòng ban và Nhân viên AI tự trị (Dynamic Agent Registry).
    Hiển thị rõ vai trò, nhiệm vụ, KPI và công cụ độc quyền.
    """
    company_code = serializers.CharField(source='company.company_code', read_only=True, allow_null=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True, allow_null=True)

    class Meta:
        model = DepartmentRegistry
        fields = [
            'id', 'company', 'company_code', 'company_name', 
            'department_code', 'agent_name', 'role_description', 
            'responsibilities', 'kpi_rules', 'required_tools', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KnowledgeFAQSerializer(serializers.ModelSerializer):
    """
    Serializer cho bảng KnowledgeFAQ phục vụ hiển thị danh sách câu hỏi mẫu (Intent FAQs).
    """
    class Meta:
        model = KnowledgeFAQ
        fields = ['id', 'question_variation', 'created_at']
        read_only_fields = ['id', 'created_at']


class KnowledgeChapterSerializer(serializers.ModelSerializer):
    """
    Serializer quản lý toàn diện thông tin KnowledgeChapter, 
    bao gồm cả danh sách các câu hỏi mẫu (faq_variations) và mã công ty chủ quản.
    """
    faq_variations = KnowledgeFAQSerializer(many=True, read_only=True)
    company_code = serializers.CharField(source='company.company_code', read_only=True, allow_null=True)

    class Meta:
        model = KnowledgeChapter
        fields = [
            'id', 
            'company',
            'company_code',
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
            'faq_variations', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class IngestTextSerializer(serializers.Serializer):
    """
    Serializer validate dữ liệu đầu vào khi nạp văn bản thô (raw_text) hoặc file.
    """
    raw_text = serializers.CharField(required=False, allow_blank=True, help_text="Nội dung văn bản thô cần bóc tách")
    company_code = serializers.CharField(required=False, default="GENERAL", help_text="Mã định danh công ty/lĩnh vực")
    domain_name = serializers.CharField(required=False, default="Quy định chung", help_text="Phân hệ nghiệp vụ lớn")
    source_file = serializers.CharField(required=False, default="Uploaded_Document.txt", help_text="Tên file gốc")
    sheet_name = serializers.CharField(required=False, allow_null=True, default=None, help_text="Tên Sheet nếu là Excel")


class ChatQuerySerializer(serializers.Serializer):
    """
    Serializer validate dữ liệu đầu vào cho API Chatbot Query toàn tập đoàn.
    """
    question = serializers.CharField(required=True, help_text="Câu hỏi của người dùng")
    company_code = serializers.CharField(required=False, allow_null=True, default=None, help_text="Lọc theo công ty con nếu có")
    domain_name = serializers.CharField(required=False, allow_null=True, default=None, help_text="Lọc theo phân hệ nghiệp vụ nếu có")
    session_id = serializers.UUIDField(required=False, allow_null=True, default=None, help_text="Mã phiên chat duy trì lịch sử Sliding Window")


class AuditDebateLogSerializer(serializers.ModelSerializer):
    """
    Serializer ghi vết nhật ký tranh biện ngầm giữa các AI Agents (BA Arbiter).
    """
    class Meta:
        model = AuditDebateLog
        fields = [
            'id', 'session', 'user_query', 'draft_response', 
            'critic_feedback', 'refine_action', 'is_conflict_detected', 
            'admin_approval_required', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class QAEvaluationLogSerializer(serializers.ModelSerializer):
    """
    Serializer nhật ký chấm điểm tự động từ Phòng QA (RAGAS Evaluator).
    """
    class Meta:
        model = QAEvaluationLog
        fields = [
            'id', 'session', 'final_answer', 'qa_score', 
            'faithfulness_score', 'relevance_score', 'passed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer quản lý chi tiết tin nhắn chat kèm metadata tương tác (Like/Dislike/Heart) 
    và cờ giám sát học tập (Supervised Learning).
    """
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'session', 'sender', 'text', 
            'metadata', 'needs_supervised_learning', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']