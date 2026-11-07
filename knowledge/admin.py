# File path: knowledge/admin.py
# Chú thích: Cấu hình giao diện Quản trị Django Admin hỗ trợ tra cứu, lọc phân cấp,
# inline FAQ và xem lịch sử chỉnh sửa tri thức (Versioning).

from django.contrib import admin
from .models import KnowledgeChapter, KnowledgeFAQ, KnowledgeHistory, ChatSession, ChatMessage


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
    list_display = ('id', 'title', 'domain_name', 'sub_domain', 'chapter_code', 'article_code', 'status', 'created_at')
    list_filter = ('status', 'domain_name', 'sub_domain', 'created_at')
    search_fields = ('title', 'content', 'summary', 'domain_name', 'sub_domain', 'source_file')
    ordering = ('-created_at',)
    inlines = [KnowledgeFAQInline, KnowledgeHistoryInline]


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'title', 'created_at', 'updated_at')
    search_fields = ('session_id', 'title')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender', 'short_text', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('text',)

    def short_text(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text
    short_text.short_description = "Nội dung"