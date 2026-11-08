# File path: knowledge/agents/dag_planner.py
# Chú thích: Master DAG Task Planner - Tự động đọc bản chỉ dẫn dự án, phân rã thành danh sách tác vụ nguyên tử (DAG Tasks) và phân công phòng ban.

import logging
import json
from typing import Dict, Any, List
from ..llm_client import query_local_llm

logger = logging.getLogger(__name__)


class DAGPlanner:
    """
    Bộ lập lịch và phân rã tác vụ DAG (Directed Acyclic Graph):
    Chuyển đổi yêu cầu từ Bản chỉ dẫn (Master Blueprint) thành các bước thực thi tuần tự,
    giao việc chính xác cho từng phòng ban AI chuyên trách.
    """

    @classmethod
    def decompose_blueprint_to_tasks(cls, blueprint_text: str) -> List[Dict[str, Any]]:
        """
        Sử dụng LLM local (qwen2.5-coder) để phân rã bản chỉ dẫn thành danh sách task có cấu trúc.
        """
        logger.info("📐 [DAG Planner] Đang phân rã Bản chỉ dẫn thành các tác vụ nguyên tử (Atomic Tasks)...")

        prompt = f"""
Bạn là Chief Architect & Master Planner của tập đoàn vnxBox Enterprise.
Dựa vào Bản chỉ dẫn hệ thống sau đây:
{blueprint_text[:3000]}

NHIỆM VỤ:
Phân rã toàn bộ dự án thành các bước thực thi tuần tự (DAG Tasks) theo thứ tự từ gốc đến ngọn (Database -> Backend Services -> Frontend UI -> QA Testing).

Trả về đúng định dạng JSON danh sách mảng thuần túy (không kèm markdown rác):
[
    {{
        "task_id": "TASK_01",
        "title": "Khởi tạo Models & Migrations cơ sở dữ liệu",
        "target_department": "DB_ARCH_DEPARTMENT",
        "assigned_agent": "Specialist_DB_01",
        "dependencies": [],
        "action_specification": "Tạo các model Django cho AgentDirectiveLog, KnowledgeChapter và cấu hình SQLite."
    }},
    {{
        "task_id": "TASK_02",
        "title": "Xây dựng Core API & Secure Sandbox",
        "target_department": "BACKEND_DEPARTMENT",
        "assigned_agent": "Specialist_IT_DEV",
        "dependencies": ["TASK_01"],
        "action_specification": "Viết các View xử lý logic chat, tích hợp Secure Sandbox và BA Arbiter."
    }}
]
"""
        res = query_local_llm(prompt, task_type="json")
        raw_response = res.get("response", "[]")

        try:
            # Làm sạch chuỗi JSON trả về
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_response:
                raw_response = raw_response.split("```")[1].split("```")[0].strip()
            
            tasks = json.loads(raw_response)
            logger.info(f"✅ [DAG Planner Success] Đã lập thành công {len(tasks)} gói tác vụ nguyên tử cho các phòng ban.")
            return tasks
        except Exception as e:
            logger.error(f"❌ [DAG Planner Error] Không thể phân rã DAG Tasks: {str(e)}")
            return []