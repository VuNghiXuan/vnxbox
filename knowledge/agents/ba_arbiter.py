# File path: knowledge/agents/ba_arbiter.py
# Chú thích: Module Phòng Trọng tài BA & Tranh biện ngầm (< 1s) tích hợp Super-Agent Vibercode Patcher tự động vá lỗi.

import logging
import json
import os
from typing import Dict, Any
from django.conf import settings
from ..models import ChatSession, AuditDebateLog, DepartmentRegistry, AgentDirectiveLog
from ..llm_client import query_local_llm
from .vibercode_patcher import VibercodePatcher

logger = logging.getLogger(__name__)


class BAArbiterEngine:
    """
    Phòng Trọng tài BA & Tranh Biện Ngầm (< 1s):
    Giám sát mâu thuẫn logic, quản lý Supervised Learning (Dislike),
    đồng thời tự động kích hoạt Vibercode Patcher để tự vá code hệ thống khi có sự cố phát sinh.
    """

    @classmethod
    def execute_debate_pipeline(cls, question: str, context_str: str, session: ChatSession = None, domain_name: str = "General") -> Dict[str, Any]:
        sys_prompt = f"Bạn là Trợ lý AI chuyên trách lĩnh vực {domain_name} của vnxBox Enterprise."
        
        draft_prompt = f"""
[NGỮ CẢNH CĂN CỨ TÀI LIỆU]:
{context_str}

[CÂU HỎI TỪ NGƯỜI DÙNG]: {question}

NHIỆM VỤ: Soạn thảo bản trả lời sơ thảo bám sát tuyệt đối tài liệu gốc. Không cắt xén điều khoản, không tự nhẩm số.
"""
        draft_res = query_local_llm(draft_prompt, system_prompt=sys_prompt, task_type="code")
        draft_text = draft_res.get("response", "Không thể sinh bản sơ thảo.")

        critic_sys_prompt = (
            "Bạn là Trọng tài BA & Kiểm toán viên Logic cấp cao của vnxBox Enterprise.\n"
            "Hãy kiểm tra bản sơ thảo: có vi phạm cắt xén văn bản không? Có hardcode hay nhẩm số không?\n"
            "Nếu hoàn toàn chính xác, hãy trả về chữ 'HOÀN HẢO'. Nếu có lỗi hoặc mâu thuẫn, hãy chỉ rõ điểm sai."
        )
        critic_prompt = f"[CÂU HỎI]: {question}\n[BẢN SƠ THẢO]: {draft_text}\n\nĐánh giá và phản biện:"
        
        critic_res = query_local_llm(critic_prompt, system_prompt=critic_sys_prompt, task_type="general")
        critic_feedback = critic_res.get("response", "HOÀN HẢO")

        is_conflict = "HOÀN HẢO" not in critic_feedback.upper()

        if is_conflict:
            refine_sys_prompt = "Bạn là Chuyên gia Gọt giũa Văn bản AGI. Hãy sửa chữa lại đáp án sơ thảo dựa trên phản biện của Trọng tài BA."
            refine_prompt = f"[SƠ THẢO]: {draft_text}\n[GÓP Ý PHẢN BIỆN]: {critic_feedback}\n\nHãy xuất ra bản câu trả lời hoàn thiện cuối cùng chuẩn xác 100%."
            refine_res = query_local_llm(refine_prompt, system_prompt=refine_sys_prompt, task_type="code")
            final_answer = refine_res.get("response", draft_text)
            refine_action = f"Đã hiệu chỉnh theo góp ý BA: {critic_feedback[:120]}..."
        else:
            final_answer = draft_text
            refine_action = "Đạt đồng thuận ngầm 100% (Không phát hiện xung đột)."

        try:
            AuditDebateLog.objects.create(
                session=session,
                user_query=question,
                draft_response=draft_text,
                critic_feedback=critic_feedback,
                refine_action=refine_action,
                is_conflict_detected=is_conflict,
                admin_approval_required=is_conflict and len(final_answer) < 20
            )
        except Exception as err:
            logger.warning(f"Không thể ghi log AuditDebateLog vào DB: {str(err)}")

        return {
            "final_answer": final_answer,
            "is_conflict": is_conflict,
            "critic_feedback": critic_feedback
        }

    @classmethod
    def process_user_dislike_correction(cls, message_obj, user_correction_note: str) -> Dict[str, Any]:
        """
        Xử lý khi người dùng Dislike. Tự động mổ xẻ lỗi, lập Thư chỉ đạo và 
        tự động kích hoạt VibercodePatcher tự chữa lành mã nguồn nếu có sự cố ngoại lệ xảy ra.
        """
        logger.info(f"🕵️ [Phòng Trọng tài BA] Tiếp nhận phiếu báo lỗi cho Tin nhắn #{message_obj.id}: '{user_correction_note}'")
        
        # 1. Bọc khối lệnh Database với cơ chế Tự chữa lành Vibercode Patcher (Self-Healing)
        try:
            metadata = message_obj.metadata or {}
            assigned_agent_name = metadata.get("assigned_agent", "Specialist_GENERAL")
            
            user_query_text = ""
            if message_obj.session:
                last_user_msg = message_obj.session.messages.filter(sender='user').last()
                if last_user_msg:
                    user_query_text = last_user_msg.text

            analysis_prompt = (
                "Bạn là Trưởng phòng Trọng tài BA Tập đoàn vnxBox Enterprise.\n"
                f"[CÂU HỎI USER]: {user_query_text}\n"
                f"[CÂU TRẢ LỜI CỦA AI]: {message_obj.text}\n"
                f"[Ý KIẾN BÁO LỖI TỪ USER]: {user_correction_note}\n\n"
                "NHIỆM VỤ:\n"
                "1. Phân tích nguyên nhân vì sao AI trả lời sai sót.\n"
                "2. Soạn thảo Quy tắc chỉ đạo (Directive) chi tiết để định hướng nhân sự AI.\n"
                "3. Đánh giá mức độ nghiêm trọng (LOW, MEDIUM, HIGH).\n\n"
                "Trả về đúng định dạng JSON thuần túy:\n"
                "{\n"
                '    "root_cause": "Mô tả nguyên nhân...",\n'
                '    "directive_instruction": "Nội dung quy tắc chỉ đạo...",\n'
                '    "severity": "LOW",\n'
                '    "require_admin_approval": false\n'
                "}"
            )
            
            ba_res = query_local_llm(analysis_prompt, task_type="json")
            raw_json = ba_res.get("response", "{}").replace("```json", "").replace("```", "").strip()
            analysis_data = json.loads(raw_json)

            target_agent = DepartmentRegistry.objects.filter(agent_name=assigned_agent_name).first()
            if not target_agent:
                target_agent = DepartmentRegistry.objects.first()

            agent_code = target_agent.agent_name if target_agent else assigned_agent_name
            need_admin = analysis_data.get("require_admin_approval", False)
            directive_status = 'PENDING_ADMIN' if need_admin else 'APPLIED'

            directive_log = AgentDirectiveLog.objects.create(
                message=message_obj,
                source_feedback=user_correction_note,
                ba_analysis=analysis_data.get("root_cause", ""),
                target_agent_code=agent_code,
                directive_content=analysis_data.get("directive_instruction", ""),
                status=directive_status
            )

            if directive_status == 'APPLIED' and target_agent:
                if not target_agent.kpi_rules:
                    target_agent.kpi_rules = {}
                if isinstance(target_agent.kpi_rules, dict):
                    directives = target_agent.kpi_rules.get("dynamic_directives", [])
                    directives.append({
                        "directive_id": directive_log.id,
                        "rule": directive_log.directive_content,
                        "issued_at": directive_log.created_at.strftime('%Y-%m-%d %H:%M')
                    })
                    target_agent.kpi_rules["dynamic_directives"] = directives
                    target_agent.save()

            return {
                "success": True,
                "directive_id": directive_log.id,
                "assigned_to": agent_code,
                "status": directive_status,
                "analysis": analysis_data
            }

        except Exception as err:
            error_msg = str(err)
            import traceback
            tb_str = traceback.format_exc()
            logger.error(f"❌ [BA Arbiter Error] Phát sinh ngoại lệ: {error_msg}. Đang kích hoạt Vibercode Patcher tự vá code...")
            
            # Kích hoạt Super-Agent Vibercode tự đọc project_map.json và tự vá lỗi hệ thống
            patch_success = VibercodePatcher.auto_repair_code_issue(error_msg, tb_str)
            
            return {
                "success": False,
                "error": error_msg,
                "vibercode_auto_patched": patch_success,
                "message": "Hệ thống đã ghi nhận lỗi và kích hoạt Super-Agent Vibercode tự động kiểm tra cấu trúc để vá lỗi."
            }