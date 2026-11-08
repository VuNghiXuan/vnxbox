# File path: knowledge/ai_services.py
# Chú thích: Engine tích hợp AI Service trung tâm cho vnxBox Enterprise (Build 2026 AGI Spec).
# Quản lý: Hardware Auto-Profiling, Multi-Model Routing, Dynamic Execution & Corporate Chat Pipeline.

import logging
import requests
import psutil
from typing import Dict, Any, List

from .sandbox import run_secure_sandbox
from .agents.router_graph import LangGraphOrchestrator
from .models import ChatSession, ChatMessage
# from .llm_client import query_local_llm

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"


# =====================================================================
# 1. HARDWARE AUTO-PROFILING & ADAPTIVE CONFIGURATION ENGINE
# =====================================================================
def profile_client_hardware() -> Dict[str, Any]:
    """Tự động quét thông số phần cứng máy khách để cấu hình Ollama tối ưu[cite: 1]."""
    try:
        mem_info = psutil.virtual_memory()
        total_ram_gb = round(mem_info.total / (1024 ** 3), 2)

        has_gpu = False
        vram_gb = 0.0
        try:
            import torch
            if torch.cuda.is_available():
                has_gpu = True
                vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
        except Exception:
            pass

        if (has_gpu and vram_gb >= 8.0) or total_ram_gb >= 32.0:
            profile_tier = "High-End"
            model_name = "qwen2.5-coder:14b" if has_gpu else "qwen2.5-coder:7b"
            num_ctx = 16384
            request_timeout = 600
        elif (has_gpu and vram_gb >= 4.0) or total_ram_gb >= 16.0:
            profile_tier = "Mid-Range"
            model_name = "qwen2.5-coder:7b"
            num_ctx = 8192
            request_timeout = 450
        else:
            profile_tier = "Low-End"
            model_name = "qwen2.5:1.5b"
            num_ctx = 4096
            request_timeout = 300

        return {
            "tier": profile_tier, "total_ram_gb": total_ram_gb, "has_gpu": has_gpu,
            "vram_gb": vram_gb, "recommended_model": model_name, "num_ctx": num_ctx,
            "request_timeout": request_timeout
        }
    except Exception as err:
        logger.warning(f"Lỗi quét phần cứng[cite: 1]: {str(err)}. Áp dụng mặc định Mid-Range.")
        return {
            "tier": "Mid-Range", "total_ram_gb": 16.0, "has_gpu": False, "vram_gb": 0.0,
            "recommended_model": "qwen2.5-coder:7b", "num_ctx": 8192, "request_timeout": 450
        }



# =====================================================================
# 2. CHAT QUERY PROCESSOR TRUNG TÂM (CORPORATE PIPELINE)
# =====================================================================
def process_corporate_chat_query(question: str, domain_name: str = None, session_id: str = None) -> Dict[str, Any]:
    """
    Điểm vào trung tâm (Entry Point) cho mọi truy vấn chat của người dùng.
    Quản lý phiên chat, ghi nhận lịch sử, ủy quyền cho LangGraphOrchestrator điều phối toàn tập đoàn,
    và trả về message_id định danh phục vụ tính năng Supervised Learning (Dislike & Mổ xẻ).
    """
    chat_session = None
    if session_id:
        chat_session, _ = ChatSession.objects.get_or_create(session_id=session_id)
        ChatMessage.objects.create(session=chat_session, sender="user", text=question)

    # Ủy quyền thực thi cho Ban Giám Đốc Tập đoàn (LangGraphOrchestrator)
    orchestration_result = LangGraphOrchestrator.process_corporate_pipeline(
        user_query=question,
        domain_name=domain_name,
        session_id=str(chat_session.session_id) if chat_session else None
    )

    final_answer = orchestration_result.get("answer", "")
    citations = orchestration_result.get("citations", [])
    sandbox_exec = orchestration_result.get("sandbox_execution", None)
    qa_score = orchestration_result.get("qa_score", 9.0)

    # Lưu vết phản hồi vào cơ sở dữ liệu phiên chat và lấy message_id thực tế
    ai_msg_id = None
    if chat_session:
        ai_msg = ChatMessage.objects.create(
            session=chat_session,
            sender="ai",
            text=final_answer,
            metadata={
                "citations": citations,
                "sandbox": sandbox_exec,
                "qa_score": qa_score,
                "department_code": orchestration_result.get("department_code"),
                "assigned_agent": orchestration_result.get("assigned_agent")
            }
        )
        ai_msg_id = ai_msg.id

    # Đính kèm message_id vào kết quả trả về để Frontend dùng cho Dislike Modal
    orchestration_result["message_id"] = ai_msg_id
    
    return orchestration_result