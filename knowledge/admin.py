from django.contrib import admin
from .models import KnowledgeChapter

@admin.register(KnowledgeChapter)
class KnowledgeChapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'domain_name', 'status', 'created_at')
    list_filter = ('status', 'domain_name', 'created_at')
    search_fields = ('title', 'summary', 'content')
    list_editable = ('status',) # Cho phép thay đổi trạng thái trực tiếp ngay ngoài danh sách
    readonly_fields = ('created_at', 'updated_at')