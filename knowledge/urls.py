# File path: knowledge/urls.py
# Chú thích: Định nghĩa API URLs cho phân hệ Knowledge Management & Chatbot Engine của vnxBox Enterprise.
# Đã bổ sung tường minh route cho endpoint Ingestion (/api/chapters/ingest/) để tránh lỗi 405 Method Not Allowed.

from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import KnowledgeChapterViewSet, chat_history_api

# Khởi tạo DefaultRouter cho các thao tác CRUD chuẩn của KnowledgeChapter
router = DefaultRouter()
router.register(r'chapters', KnowledgeChapterViewSet, basename='knowledge-chapter')

urlpatterns = [
    # Đăng ký tường minh endpoint Ingestion nạp file trước router để nhận diện phương thức POST
    path('chapters/ingest/', KnowledgeChapterViewSet.as_view({'post': 'ingest'}), name='knowledge-ingest'),
    
    # Lịch sử chat phiên làm việc
    path('chat/history/', chat_history_api, name='chat_history_api'),
] + router.urls