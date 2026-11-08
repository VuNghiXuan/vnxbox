# File path: knowledge/views.py
# Chú thích: Django REST Framework ViewSets & API Views cho phân hệ vnxBox Enterprise.
# Đã tích hợp đầy đủ: Quản lý tiến độ nhân sự AI, Tranh biện & Tự sửa lỗi, Lịch sử Chat có Thả tim/Like/Dislike, 
# Giám sát học tập có giám sát (Supervised Learning), và định danh message_id chính xác để triệt tiêu lỗi undefined.

import json
import logging
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

from .models import (
    ChatSession, ChatMessage, KnowledgeChapter, KnowledgeHistory, 
    DepartmentRegistry, AuditDebateLog, QAEvaluationLog, CompanyDomain, KnowledgeFAQ
)
from .serializers import KnowledgeChapterSerializer
from .sandbox import run_secure_sandbox

from django.shortcuts import render

# 1. Các hàm gọi LLM cơ bản lấy từ llm_client
from .llm_client import query_local_llm, OLLAMA_API_URL, LOCAL_MODEL_NAME

# 2. Các hàm xử lý logic nghiệp vụ tập đoàn & RAG lấy từ ai_services
from .ai_services import (
    process_corporate_chat_query, 
    profile_client_hardware,
)
from .parsers.taxonomy_engine import TaxonomyEngine
from .agents.ba_arbiter import BAArbiterEngine

logger = logging.getLogger(__name__)


def _clean_json_response(raw_text: str) -> str:
    """Làm sạch chuỗi JSON trả về từ LLM."""
    if not raw_text:
        return "{}"
    return raw_text.replace("```json", "").replace("```", "").strip()


class KnowledgeChapterViewSet(viewsets.ModelViewSet):
    """
    ViewSet quản lý toàn bộ vòng đời tri thức doanh nghiệp & Vận hành Tập đoàn AI.
    """
    queryset = KnowledgeChapter.objects.all().order_by('-created_at')
    serializer_class = KnowledgeChapterSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'domain_name', 'sub_domain']
    search_fields = ['title', 'summary', 'content', 'sub_domain', 'chapter_code', 'article_code']
    ordering_fields = ['created_at', 'updated_at', 'title']
    
    @action(detail=False, methods=['post'])
    def ingest(self, request):
        """API Ingestion tài liệu đa định dạng, tích hợp Router bóc tách chuyên sâu cho .docx, .xlsx, .pdf, ảnh."""
        company_code = request.data.get("company_code", "GENERAL") or request.POST.get("company_code", "GENERAL")
        domain_name = request.data.get("domain_name", "Quy định chung") or request.POST.get("domain_name", "Quy định chung")
        
        uploaded_file = request.FILES.get("file")
        raw_text = request.data.get("raw_text", "").strip() or request.POST.get("raw_text", "").strip()

        # 1. Trường hợp người dùng tải file lên qua Ingestion Router (file_parsers.py)
        if uploaded_file:
            try:
                from .file_parsers import parse_uploaded_file
                parse_result = parse_uploaded_file(uploaded_file, default_company_code=company_code, default_domain=domain_name)
                
                if not parse_result.get("success"):
                    return Response({"success": False, "error": parse_result.get("error", "Lỗi bóc tách file.")}, status=status.HTTP_400_BAD_REQUEST)
                
                created_chapters = []
                for ch_data in parse_result.get("chapters", []):
                    chapter_obj = KnowledgeChapter.objects.create(
                        title=ch_data.get("title", "Điều khoản mới"),
                        source_file=ch_data.get("source_file", uploaded_file.name),
                        sheet_name=ch_data.get("sheet_name"),
                        domain_name=ch_data.get("domain_name", domain_name),
                        sub_domain=ch_data.get("sub_domain", "Quy định chung"),
                        chapter_code=ch_data.get("chapter_code", "Chương I"),
                        article_code=ch_data.get("article_code", "Điều 1"),
                        summary=ch_data.get("summary", ""),
                        content=ch_data.get("content", ""),
                        status="AUTO_APPROVED",
                        metadata={
                            "assigned_agent": ch_data.get("assigned_agent"),
                            "faq_variations": ch_data.get("intent_faqs", [])
                        }
                    )
                    
                    # 🔥 TỰ ĐỘNG TẠO BẢN GHI FAQ TRONG DATABASE CHO FILE
                    faqs_list = ch_data.get("intent_faqs", []) or ch_data.get("faq_variations", [])
                    for q_text in faqs_list:
                        if q_text and q_text.strip():
                            KnowledgeFAQ.objects.create(
                                chapter=chapter_obj,
                                question_variation=q_text.strip()
                            )

                    created_chapters.append(chapter_obj.id)

                return Response({
                    "success": True,
                    "message": f"Nạp và bóc tách thành công {len(created_chapters)} phân đoạn tri thức từ file!",
                    "chapter_ids": created_chapters
                }, status=status.HTTP_201_CREATED)

            except Exception as err:
                logger.error(f"Lỗi Ingestion Router với file: {str(err)}", exc_info=True)
                return Response({"success": False, "error": f"Lỗi xử lý file: {str(err)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Trường hợp nạp bằng văn bản thô (Raw Text) nhập trực tiếp
        if not raw_text:
            return Response({"success": False, "error": "⚠️ Thiếu nội dung văn bản thô (raw_text) hoặc file tải lên."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            classification_res = TaxonomyEngine.analyze_and_classify_chunk(
                raw_chunk_text=raw_text,
                default_company_code=company_code,
                default_domain=domain_name
            )

            chapter_obj = KnowledgeChapter.objects.create(
                title=classification_res.get("title", "Điều khoản mới"),
                source_file="Manual_Raw_Text.txt",
                sheet_name=None,
                domain_name=classification_res.get("domain_name", domain_name),
                sub_domain=classification_res.get("sub_domain", "Quy định chung"),
                chapter_code=classification_res.get("chapter_code", "Chương I"),
                article_code=classification_res.get("article_code", "Điều 1"),
                summary=classification_res.get("summary", ""),
                content=raw_text,
                status="AUTO_APPROVED",
                metadata={
                    "assigned_agent": classification_res.get("assigned_agent_name"),
                    "faq_variations": classification_res.get("faq_variations", [])
                }
            )

            # 🔥 TỰ ĐỘNG TẠO BẢN GHI FAQ TRONG DATABASE CHO RAW TEXT
            faqs_list = classification_res.get("faq_variations", [])
            for q_text in faqs_list:
                if q_text and q_text.strip():
                    KnowledgeFAQ.objects.create(
                        chapter=chapter_obj,
                        question_variation=q_text.strip()
                    )

            return Response({
                "success": True,
                "message": "Nạp văn bản thô và tự động sinh nhân sự tập đoàn thành công!",
                "chapter_id": chapter_obj.id,
                "taxonomy_result": classification_res
            }, status=status.HTTP_201_CREATED)
            
        except Exception as err:
            logger.error(f"Lỗi Ingestion Raw Text: {str(err)}")
            return Response({"success": False, "error": str(err)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def run_sandbox(self, request):
        """API thực thi mã Python an toàn trong Secure Sandbox (Triệt tiêu ảo giác toán học)."""
        code = request.data.get("code", "")
        timeout_seconds = int(request.data.get("timeout", 3))
        if not code:
            return Response({"success": False, "error": "⚠️ Thiếu đoạn code Python."}, status=status.HTTP_400_BAD_REQUEST)
        result = run_secure_sandbox(code_str=code, timeout_seconds=timeout_seconds)
        return Response(result, status=status.HTTP_200_OK)

    
    @action(detail=False, methods=['post'])
    def chat_query(self, request):
        """
        API Chatbot Tập Đoàn AI: 
        Được gác cổng bởi Viber Intent Router và hỗ trợ bóc tách file đính kèm thực tế.
        """
        question = request.data.get("question", "").strip()
        domain_name = request.data.get("domain_name", "Quy định chung")
        session_id = request.data.get("session_id", None)
        uploaded_file = request.FILES.get("file", None)

        if not question and not uploaded_file:
            return Response({"success": False, "error": "⚠️ Vui lòng cung cấp nội dung câu hỏi hoặc tệp đính kèm."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            extracted_file_context = ""
            
            # 1. Nếu Sếp có đính kèm file -> Gọi ViberDoclingParser bóc tách ngay lập tức
            if uploaded_file:
                from knowledge.agents.viber_docling_parser import ViberDoclingParser
                parse_res = ViberDoclingParser.parse_document(uploaded_file)
                
                if parse_res.get("status") == "success":
                    extracted_file_context = parse_res.get("extracted_markdown", "")
                    
                    # Tự động lưu bản ghi tri thức vào Database để hệ thống học luôn
                    KnowledgeChapter.objects.create(
                        title=f"Tài liệu đính kèm: {uploaded_file.name}",
                        source_file=uploaded_file.name,
                        domain_name=domain_name,
                        sub_domain="Tài liệu nghiệp vụ",
                        chapter_code="Chương I",
                        article_code="Điều 1",
                        summary=f"Bóc tách tự động từ tệp {uploaded_file.name} qua Viber Docling Parser.",
                        content=extracted_file_context,
                        status="AUTO_APPROVED"
                    )
                    logger.info(f"💾 [Ingestion Success] Đã lưu tri thức từ file {uploaded_file.name} vào Database.")
                else:
                    return Response({"success": False, "error": f"Lỗi bóc tách file: {parse_res.get('message')}"}, status=status.HTTP_400_BAD_REQUEST)

            # Gộp nội dung file bóc tách vào câu hỏi nếu có
            full_prompt = question
            if extracted_file_context:
                full_prompt = f"Dựa trên nội dung tài liệu đính kèm sau:\n{extracted_file_context}\n\nYêu cầu từ Sếp: {question}"

            # 2. Phân tích ý định qua Viber Intent Router
            from knowledge.agents.viber_intent_router import ViberIntentRouter
            intent_result = ViberIntentRouter.classify_intent(full_prompt)
            intent_type = intent_result.get("intent_type")

            # 3. Điều phối hành động
            if intent_type == "CORPORATE_ACTION" or uploaded_file:
                from knowledge.agents.execution_dispatcher import ExecutionDispatcher
                from knowledge.agents.viber_test_generator import ViberTestGenerator
                
                pipeline_results = ExecutionDispatcher.run_corporation_pipeline(full_prompt)
                test_report = ViberTestGenerator.generate_detailed_test_cases(
                    feature_title=f"Xử lý tài liệu & tác vụ: {uploaded_file.name if uploaded_file else 'Yêu cầu hệ thống'}",
                    feature_specification=full_prompt
                )
                
                result = {
                    "success": True,
                    "type": "corporate_action",
                    "intent": intent_result,
                    "message": f"⚡ Tập đoàn AI đã bóc tách thành công {'tệp ' + uploaded_file.name if uploaded_file else 'yêu cầu'} và hoàn thành chuỗi tác vụ!",
                    "tasks": pipeline_results,
                    "test_report": test_report
                }
            else:
                result = process_corporate_chat_query(
                    question=full_prompt,
                    domain_name=domain_name,
                    session_id=session_id
                )
                result["intent"] = intent_result
            
            # Gán message_id gần nhất nếu có session
            if session_id:
                try:
                    session_obj = ChatSession.objects.filter(session_id=session_id).first()
                    if session_obj:
                        latest_ai_msg = session_obj.messages.filter(sender='ai').order_by('-created_at').first()
                        if latest_ai_msg:
                            result["message_id"] = latest_ai_msg.id
                except Exception as db_err:
                    logger.warning(f"Không thể gán message_id: {str(db_err)}")

            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Lỗi thực thi Chat Query: {str(e)}", exc_info=True)
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def corporation_status(self, request):
        """
        📊 API Dashboard: Giám sát toàn cảnh Tập đoàn AI.
        Hiển thị danh sách phòng ban, nhân viên AI đang hoạt động, nhiệm vụ được giao, 
        tiến độ, khó khăn (bottleneck) và thống kê tranh biện / QA logs.
        """
        try:
            departments = DepartmentRegistry.objects.filter(is_active=True)
            agent_list = []
            for agent in departments:
                agent_list.append({
                    "department_code": agent.department_code,
                    "agent_name": agent.agent_name,
                    "role_description": agent.role_description,
                    "responsibilities": agent.responsibilities,
                    "kpi_rules": agent.kpi_rules,
                    "status": "Đang sẵn sàng / Đang thực thi",
                    "difficulties": None if agent.is_active else "Đang tạm khóa để tối ưu"
                })

            recent_debates = AuditDebateLog.objects.order_by('-created_at')[:5]
            debate_summary = [
                {
                    "query": log.user_query[:60],
                    "is_conflict": log.is_conflict_detected,
                    "refine_action": log.refine_action,
                    "created_at": log.created_at.strftime('%Y-%m-%d %H:%M')
                } for log in recent_debates
            ]

            recent_qa = QAEvaluationLog.objects.order_by('-created_at')[:5]
            qa_summary = [
                {
                    "score": log.qa_score,
                    "passed": log.passed,
                    "created_at": log.created_at.strftime('%Y-%m-%d %H:%M')
                } for log in recent_qa
            ]

            return Response({
                "success": True,
                "total_departments": departments.count(),
                "active_agents": agent_list,
                "recent_debates": debate_summary,
                "recent_qa_evaluations": qa_summary
            }, status=status.HTTP_200_OK)
        except Exception as err:
            logger.error(f"Lỗi lấy trạng thái tập đoàn: {str(err)}")
            return Response({"success": False, "error": str(err)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatInteractionAPIView(viewsets.ViewSet):
    """
    API quản lý tương tác tin nhắn: Thả tim, Like, Dislike, phản hồi học tập có giám sát (Supervised Learning).
    """

    @action(detail=True, methods=['post'])
    def react_message(self, request, pk=None):
        """
        Ghi nhận phản hồi tương tác (Like, Dislike, Love/Heart) của người dùng trên từng tin nhắn AI.
        Nếu Dislike, hệ thống kích hoạt BA Arbiter mổ xẻ vấn đề và tự học ngầm.
        """
        if not pk or pk == 'undefined':
            return Response({"success": False, "error": "ID tin nhắn không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

        reaction_type = request.data.get("reaction", "like") # like, dislike, love
        feedback_note = request.data.get("note", "").strip()

        try:
            msg = ChatMessage.objects.get(pk=pk)
            if not msg.metadata:
                msg.metadata = {}
            
            # Cập nhật số liệu reactions
            reactions = msg.metadata.get("reactions", {"like": 0, "dislike": 0, "love": 0})
            if reaction_type in reactions:
                reactions[reaction_type] += 1
            msg.metadata["reactions"] = reactions
            msg.metadata["user_feedback_note"] = feedback_note

            # Nếu Dislike, bật cờ supervised learning và gọi BA Arbiter tự hoàn thiện ngầm
            if reaction_type == "dislike":
                msg.needs_supervised_learning = True
                logger.warning(f"⚠️ Phát hiện Dislike cho tin nhắn #{pk} với ghi chú: '{feedback_note}'. Đã kích hoạt AI BA Self-Correction.")
                
                try:
                    BAArbiterEngine.process_user_dislike_correction(
                        message_obj=msg,
                        user_correction_note=feedback_note
                    )
                except Exception as ba_err:
                    logger.error(f"Lỗi BA Arbiter xử lý Dislike correction: {str(ba_err)}", exc_info=True)

            msg.save()

            return Response({
                "success": True,
                "message": "Cảm ơn Vũ! Hệ thống đã ghi nhận phản hồi và AI BA đang tiến hành mổ xẻ, cập nhật lại quy tắc ngầm.",
                "reactions": reactions
            }, status=status.HTTP_200_OK)
            
        except ChatMessage.DoesNotExist:
            return Response({"success": False, "error": "Không tìm thấy tin nhắn."}, status=status.HTTP_404_NOT_FOUND)


def chat_history_api(request):
    """API lấy lịch sử đoạn chat theo session_id kèm theo metadata reactions."""
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({"success": True, "messages": []})
    
    try:
        session = ChatSession.objects.get(session_id=session_id)
        msgs = session.messages.order_by('created_at')
        data = [
            {
                "id": m.id,
                "sender": m.sender,
                "text": m.text,
                "metadata": m.metadata
            } 
            for m in msgs
        ]
        return JsonResponse({"success": True, "messages": data})
    except ChatSession.DoesNotExist:
        return JsonResponse({"success": True, "messages": []})


def viber_chat_view(request):
    return render(request, 'knowledge/viber_chat.html')