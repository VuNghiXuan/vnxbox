# File path: knowledge/urls.py
# Chú thích: Đặt viber_chat_view làm trang chủ chính thức của hệ thống vnxBox Enterprise.

from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import KnowledgeChapterViewSet, ChatInteractionAPIView, chat_history_api, viber_chat_view
from knowledge.agents.viber_war_room_view import viber_war_room_dashboard, api_run_corporation_trigger

# Khởi tạo DefaultRouter
router = DefaultRouter()
router.register(r'chapters', KnowledgeChapterViewSet, basename='knowledge-chapter')
router.register(r'chat-interactions', ChatInteractionAPIView, basename='chat-interactions')

urlpatterns = [
    # ⚡ ĐẶT GIAO DIỆN CHAT LÀM TRANG CHỦ MẶC ĐỊNH (ROOT URL)
    path('', viber_chat_view, name='viber_chat_root'),

    # 1. Các Action endpoints cho KnowledgeChapter
    path('chapters/ingest/', KnowledgeChapterViewSet.as_view({'post': 'ingest'}), name='knowledge-ingest'),
    path('chapters/run_sandbox/', KnowledgeChapterViewSet.as_view({'post': 'run_sandbox'}), name='knowledge-run-sandbox'),
    path('chapters/chat_query/', KnowledgeChapterViewSet.as_view({'post': 'chat_query'}), name='knowledge-chat-query'),
    path('chapters/corporation_status/', KnowledgeChapterViewSet.as_view({'get': 'corporation_status'}), name='knowledge-corporation-status'),
    
    # 2. Lịch sử chat phiên làm việc
    path('chat/history/', chat_history_api, name='chat_history_api'),

    # Giao diện vibecode & War Room
    path('war-room/', viber_war_room_dashboard, name='viber_war_room'),
    path('war-room/api/run/', api_run_corporation_trigger, name='api_run_corporation'),
    path('chat/', viber_chat_view, name='viber_chat_interface'),
] + router.urls