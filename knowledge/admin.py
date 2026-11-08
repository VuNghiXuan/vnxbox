# File path: knowledge/admin.py
# Chú thích: Cấu hình giao diện Quản trị Django Admin hỗ trợ tra cứu, lọc phân cấp,
# inline FAQ, lịch sử chỉnh sửa (Versioning), quản lý Công ty con, Nhân viên AI, 
# và các nhật ký kiểm toán tranh biện/QA cho vnxBox Enterprise.

from django.contrib import admin
from .models import (
    CompanyDomain, DepartmentRegistry, KnowledgeChapter, 
    KnowledgeFAQ, KnowledgeHistory, ChatSession, ChatMessage, 
    AuditDebateLog, QAEvaluationLog
)


@admin.register(CompanyDomain)
class CompanyDomainAdmin(admin.ModelAdmin):
    list_display = ('id', 'company_code', 'company_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('company_code', 'company_name', 'description')
    ordering = ('company_code',)


@admin.register(DepartmentRegistry)
class DepartmentRegistryAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'department_code', 'agent_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'company', 'created_at')
    search_fields = ('agent_name', 'department_code', 'role_description', 'responsibilities')
    ordering = ('department_code',)


class KnowledgeFAQInline(admin.TabularInline):
    model = KnowledgeFAQ
    extra = 1
    fields = ('question_variation',)


class KnowledgeHistoryInline(admin.StackedInline):
    model = KnowledgeHistory
    extra = 0
    readonly_fields = ('version', 'content_before', 'content_after', 'prompt_instruction', 'created_by', 'created_at')
    can_delete = False


@admin.register(KnowledgeChapter)
class KnowledgeChapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'company', 'domain_name', 'sub_domain', 'chapter_code', 'article_code', 'status', 'created_at')
    list_filter = ('status', 'company', 'domain_name', 'sub_domain', 'created_at')
    search_fields = ('title', 'content', 'summary', 'domain_name', 'sub_domain', 'source_file')
    ordering = ('-created_at',)
    inlines = [KnowledgeFAQInline, KnowledgeHistoryInline]


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'title', 'created_at', 'updated_at')
    search_fields = ('session_id', 'title')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender', 'short_text', 'needs_supervised_learning', 'created_at')
    list_filter = ('sender', 'needs_supervised_learning', 'created_at')
    search_fields = ('text',)

    def short_text(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text
    short_text.short_description = "Nội dung"


@admin.register(AuditDebateLog)
class AuditDebateLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'short_query', 'is_conflict_detected', 'admin_approval_required', 'created_at')
    list_filter = ('is_conflict_detected', 'admin_approval_required', 'created_at')
    search_fields = ('user_query', 'draft_response', 'critic_feedback', 'refine_action')

    def short_query(self, obj):
        return obj.user_query[:50] + "..." if len(obj.user_query) > 50 else obj.user_query
    short_query.short_description = "Truy vấn gốc"


@admin.register(QAEvaluationLog)
class QAEvaluationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'qa_score', 'faithfulness_score', 'relevance_score', 'passed', 'created_at')
    list_filter = ('passed', 'created_at')
    search_fields = ('final_answer',)
    ordering = ('-created_at',)