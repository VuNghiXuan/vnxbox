# File path: knowledge/views.py
# Chú thích: Django REST Framework ViewSets & API Views cho phân hệ Knowledge Management & Chatbot Engine 
# của vnxBox Enterprise. Hỗ trợ Ingestion, Secure Sandbox, Hybrid Chat Query, Full Versioning (Audit Trail)
# và tích hợp Hardware Auto-Profiling chống nghẽn ReadTimeout.

import json
import logging
import requests
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

from .models import ChatSession, KnowledgeChapter, KnowledgeHistory
from .serializers import KnowledgeChapterSerializer
from .sandbox import run_secure_sandbox
from .ai_services import (
    process_ingest_document, 
    process_ingest_file, 
    process_chat_query,
    profile_client_hardware,
    OLLAMA_API_URL,
    LOCAL_MODEL_NAME
)

logger = logging.getLogger(__name__)


def _clean_json_response(raw_text: str) -> str:
    """
    Làm sạch chuỗi JSON trả về từ LLM (bọc trong ```json ... ``` hoặc ``` ... ```).
    """
    if not raw_text:
        return "{}"
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    return cleaned


class KnowledgeChapterViewSet(viewsets.ModelViewSet):
    """
    ViewSet quản lý toàn bộ vòng đời tri thức doanh nghiệp 
    (CRUD + Custom Actions cho Ingest, Chat, Sandbox & AI Recompile)
    """
    queryset = KnowledgeChapter.objects.all().order_by('-created_at')
    serializer_class = KnowledgeChapterSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'domain_name', 'sub_domain']
    search_fields = ['title', 'summary', 'content', 'sub_domain', 'chapter_code', 'article_code']
    ordering_fields = ['created_at', 'updated_at', 'title']
    
    @action(detail=False, methods=['post'])
    def ingest(self, request):
        """
        API thông minh nhận văn bản thô (raw_text) hoặc file tải lên (PDF, Word, Excel, CSV, TXT, MD, Ảnh/Scan).
        Chuyển giao cho AI Service bóc tách, băm Chunk, sinh FAQ và lưu vào DB (Hỗ trợ Async Threading chống treo giao diện).
        """
        domain_name = request.data.get("domain_name", "Quy định chung")
        scope = request.data.get("scope", "Toàn hệ thống")
        uploaded_file = request.FILES.get("file", None)
        raw_text = request.data.get("raw_text", "")

        if uploaded_file:
            result = process_ingest_file(file_obj=uploaded_file, domain_name=domain_name, scope=scope)
        elif raw_text:
            result = process_ingest_document(raw_text=raw_text, domain_name=domain_name, scope=scope)
        else:
            return Response(
                {"success": False, "error": "⚠️ Vui lòng cung cấp nội dung văn bản thô (raw_text) hoặc tải lên tệp tin (file)."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not result.get("success", False):
            return Response({"success": False, "error": result.get("error", "Lỗi bóc tách không xác định")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(result.get("chapter"))
        return Response({
            "success": True,
            "message": "Bóc tách tri thức và sinh câu hỏi mẫu thành công bởi Local AI (Ollama)!",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def run_sandbox(self, request):
        """
        API thực thi mã Python tính toán an toàn trong Secure Code Sandbox (triệt tiêu ảo giác toán học).
        """
        code = request.data.get("code", "")
        timeout_seconds = int(request.data.get("timeout", 3))

        if not code:
            return Response({"success": False, "error": "⚠️ Thiếu đoạn code Python cần chạy trong Sandbox."}, status=status.HTTP_400_BAD_REQUEST)

        result = run_secure_sandbox(code_str=code, timeout_seconds=timeout_seconds)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def chat_query(self, request):
        """
        API Chatbot chính: Nhận câu hỏi và session_id, kết hợp Lịch sử chat (Sliding Window),
        Intent Routing + Hybrid Search và gọi Ollama trả lời kèm citations sâu.
        """
        question = request.data.get("question", "").strip()
        domain_name = request.data.get("domain_name", None)
        session_id = request.data.get("session_id", None)

        logger.info(f"ChatQuery Request -> Question: '{question}' | Domain: {domain_name} | Session: {session_id}")

        if not question:
            return Response({"success": False, "error": "⚠️ Vui lòng cung cấp nội dung câu hỏi."}, status=status.HTTP_400_BAD_REQUEST)

        # Gọi service xử lý chat chuyên sâu
        result = process_chat_query(question=question, domain_name=domain_name, session_id=session_id)

        if not result.get("success", False):
            if result.get("refusal"):
                return Response(result, status=status.HTTP_200_OK)
            return Response({"success": False, "error": result.get("error", "Lỗi xử lý hệ thống Chat")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "success": True,
            "session_id": result.get("session_id"),
            "question": question,
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "sandbox_execution": result.get("sandbox_execution")
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def recompile_with_ai(self, request, pk=None):
        """
        API cho phép Admin yêu cầu AI biên soạn/tái cấu trúc lại nội dung tri thức.
        Tự động áp dụng Hardware Auto-Profiling để cấp phát timeout linh hoạt chống lỗi ReadTimeout.
        Đồng thời ghi nhận lịch sử vào bảng KnowledgeHistory (Full Versioning & Audit Trail).
        """
        chapter = self.get_object()
        custom_instruction = request.data.get(
            "instruction", 
            "Hãy biên soạn, chuẩn hóa lại nội dung này mạch lạc, rõ ràng hơn và giữ nguyên vẹn dữ liệu gốc."
        )
        created_by = request.data.get("created_by", "Admin / AI Recompile")

        prompt = f"""
Bạn là biên tập viên tri thức doanh nghiệp. Hãy biên soạn lại nội dung tri thức dưới đây theo yêu cầu của quản trị viên.

YÊU CẦU BIÊN SOẠN: {custom_instruction}

TIÊU ĐỀ GỐC: {chapter.title}
NỘI DUNG GỐC:
{chapter.content}

Trích xuất kết quả dưới dạng JSON thuần túy (không kèm markdown):
{{
    "new_title": "Tiêu đề sau biên soạn",
    "new_summary": "Tóm tắt mới",
    "new_content": "Nội dung chi tiết đã được biên soạn, chuẩn hóa sạch sẽ"
}}
"""
        # Lấy thông số cấu hình phần cứng động để cấp phát timeout chuẩn xác
        hw_profile = profile_client_hardware()
        dynamic_timeout = hw_profile.get("request_timeout", 600)

        payload = {
            "model": hw_profile.get("recommended_model", LOCAL_MODEL_NAME),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": hw_profile.get("num_ctx", 8192)
            }
        }

        try:
            ai_res = requests.post(OLLAMA_API_URL, json=payload, timeout=dynamic_timeout)
            if ai_res.status_code != 200:
                return Response({"success": False, "error": "⚠️ Lỗi kết nối Ollama khi biên soạn lại tri thức."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            res_json = ai_res.json()
            raw_response = res_json.get("response", "{}")
            ai_data = json.loads(_clean_json_response(raw_response))

            # 1. Lưu lại nội dung cũ trước khi thay đổi vào bảng KnowledgeHistory (Full Versioning)
            current_version_count = chapter.histories.count() + 1
            KnowledgeHistory.objects.create(
                chapter=chapter,
                version=current_version_count,
                content_before=chapter.content,
                content_after=ai_data.get("new_content", chapter.content),
                prompt_instruction=custom_instruction,
                created_by=created_by
            )

            # 2. Cập nhật thông tin mới vào Chapter
            chapter.title = ai_data.get("new_title", chapter.title)
            chapter.summary = ai_data.get("new_summary", chapter.summary)
            chapter.content = ai_data.get("new_content", chapter.content)
            chapter.status = "AUTO_APPROVED"
            chapter.save()  # Kích hoạt signal Auto Re-Index tự động

            serializer = self.get_serializer(chapter)
            return Response({
                "success": True,
                "message": "AI đã biên soạn lại tri thức và ghi nhận lịch sử phiên bản thành công!",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except requests.exceptions.ReadTimeout:
            logger.error(f"ReadTimeoutError: AI Recompile quá thời gian ({dynamic_timeout}s) cho chapter {pk}.")
            return Response({"success": False, "error": f"⚠️ Mô hình AI xử lý quá thời gian quy định ({dynamic_timeout}s). Vui lòng chia nhỏ tài liệu."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Lỗi khi recompile chapter {pk}: {str(e)}", exc_info=True)
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def chat_history_api(request):
    """
    API lấy lịch sử đoạn chat theo session_id phục vụ khôi phục giao diện người dùng.
    """
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({"success": True, "messages": []})
    
    try:
        session = ChatSession.objects.get(session_id=session_id)
        msgs = session.messages.order_by('created_at')
        data = [
            {
                "sender": m.sender,
                "text": m.text,
                "metadata": m.metadata
            } 
            for m in msgs
        ]
        return JsonResponse({"success": True, "messages": data})
    except ChatSession.DoesNotExist:
        return JsonResponse({"success": True, "messages": []})