# File path: knowledge/middleware.py
# Chú thích: Middleware tự động bẫy lỗi hệ thống, kích hoạt AI BA phân tích và tự động vá lỗi (Self-Healing).

import logging
import traceback
from django.db import connection
from django.core.management import call_command
from .models import AgentDirectiveLog, DepartmentRegistry
from .llm_client import query_local_llm

logger = logging.getLogger(__name__)


class AutonomousSelfHealingMiddleware:
    """
    Trạm gác tự trị: Bắt lỗi runtime, giao cho AI BA chẩn đoán nguyên nhân,
    tự động kích hoạt cơ chế tự chữa lành (Self-Healing) nếu là lỗi Database/Migration.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        error_msg = str(exception)
        tb_str = traceback.format_exc()
        
        logger.error(f"🚨 [Self-Healing Daemon] Phát hiện lỗi hệ thống: {error_msg}")

        # 1. Kiểm tra nếu là lỗi thiếu bảng database (OperationalError: no such table) -> Tự động chữa lành!
        if "no such table" in error_msg.lower():
            logger.info("🛠️ [Auto-Heal] Phát hiện thiếu cấu trúc bảng Database. Đang tự động kích hoạt lệnh migrate...")
            try:
                call_command('makemigrations', interactive=False)
                call_command('migrate', interactive=False)
                logger.info("✅ [Auto-Heal Success] Đã tự động tạo bảng và đồng bộ Database thành công! Hệ thống đã phục hồi.")
            except Exception as migrate_err:
                logger.error(f"❌ [Auto-Heal Failed] Không thể tự động migrate: {str(migrate_err)}")

        # 2. Giao việc cho AI BA phân tích nguyên nhân và ghi nhật ký AgentDirectiveLog tự động
        try:
            analysis_prompt = f"""
Bạn là Trưởng phòng Trọng tài BA Tập đoàn vnxBox Enterprise.
Hệ thống vừa gặp ngoại lệ (Exception): {error_msg}
Stack Trace:
{tb_str[:1000]}

NHIỆM VỤ:
1. Phân tích nguyên nhân gốc rễ (Root Cause) của lỗi này trên mã nguồn Django.
2. Đề xuất hành động sửa lỗi cụ thể cho Dev Agent (Ví dụ: Chạy lệnh gì, sửa file nào).

Trả về đúng định dạng JSON:
{{"root_cause": "...", "directive_instruction": "...", "severity": "HIGH"}}
"""
            ba_res = query_local_llm(analysis_prompt, task_type="json")
            import json
            raw_json = ba_res.get("response", "{}").replace("```json", "").replace("```", "").strip()
            analysis_data = json.loads(raw_json)

            # Ghi vào bảng quản trị AgentDirectiveLog để Sếp theo dõi trên War Room
            target_agent = DepartmentRegistry.objects.filter(agent_name="Specialist_IT_DEV").first()
            if not target_agent:
                target_agent = DepartmentRegistry.objects.first()

            AgentDirectiveLog.objects.create(
                source_feedback=f"System Error: {error_msg}",
                ba_analysis=analysis_data.get("root_cause", error_msg),
                target_agent_code=target_agent.agent_name if target_agent else "DEV_AGENT",
                directive_content=analysis_data.get("directive_instruction", "Kiểm tra lại log hệ thống."),
                status="APPLIED" if "no such table" in error_msg.lower() else "PENDING_ADMIN"
            )
            logger.info("📋 [AI BA Dispatcher] Đã tự động lập Thư chỉ đạo xử lý lỗi cho đội ngũ IT Dev.")
        except Exception as log_err:
            logger.warning(f"⚠️ Không thể ghi log tự động cho BA: {str(log_err)}")

        return None