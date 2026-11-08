# File path: knowledge/agents/vibercode_patcher.py
# Chú thích: Tích hợp bộ lọc làm sạch JSON tự động chống lỗi cú pháp khi giao tiếp với LLM.

import os
import json
import logging
import re
from django.conf import settings
from ..llm_client import query_local_llm

logger = logging.getLogger(__name__)


class VibercodePatcher:
    @staticmethod
    def get_project_map():
        map_path = os.path.join(settings.BASE_DIR, "project_map.json")
        if not os.path.exists(map_path):
            return {}
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def clean_and_parse_json(raw_text: str) -> dict:
        """
        Làm sạch chuỗi trả về từ LLM, loại bỏ markdown block và trích xuất đúng cấu trúc JSON.
        """
        if not raw_text:
            return {}
        
        # 1. Cố gắng tìm đoạn nằm trong ```json ... ```
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
        if match:
            json_str = match.group(1)
        else:
            json_str = raw_text

        # 2. Làm sạch ký tự điều khiển và khoảng trắng thừa
        json_str = json_str.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [JSON Parse Warning] Lỗi phân tích JSON trực tiếp: {str(e)}. Đang thử trích xuất phần ngoặc nhọn...")
            # Thử tìm vóc dáng JSON từ dấu { đầu tiên đến } cuối cùng
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    sub_str = json_str[start_idx:end_idx+1]
                    return json.loads(sub_str)
                except Exception:
                    pass
        return {}

    @classmethod
    def auto_repair_code_issue(cls, error_message: str, traceback_str: str) -> bool:
        """
        Tự động đọc project_map.json, định vị file và vá code thông minh.
        """
        logger.info("🤖 [Vibercode Patcher] Đang phân tích cấu trúc dự án để tự vá lỗi...")
        
        project_map = cls.get_project_map()
        dirs_summary = project_map.get('directories', {})

        prompt = f"""
Bạn là Super-Agent Vibercode Master Developer của vnxBox Enterprise.
Hệ thống gặp lỗi runtime sau:
Lỗi: {error_message}

Một số thư mục trong dự án:
{json.dumps(list(dirs_summary.keys()), ensure_ascii=False)}

NHIỆM VỤ:
Trả về duy nhất một đối tượng JSON thuần túy (không kèm bất kỳ văn bản nào ngoài JSON) theo đúng cấu trúc sau:
{{
    "target_file_path": "knowledge/agents/ba_arbiter.py",
    "repair_action": "Mô tả ngắn gọn cách sửa",
    "full_fixed_code_or_patch": "# Nội dung code thay thế hoặc ghi chú sửa lỗi"
}}
"""
        res = query_local_llm(prompt, task_type="json")
        raw_response = res.get("response", "{}")
        
        data = cls.clean_and_parse_json(raw_response)
        if not data:
            logger.error("❌ [Vibercode Patcher] Không thể trích xuất được JSON hợp lệ từ LLM response.")
            return False

        target_file = data.get("target_file_path", "").strip()
        fixed_code = data.get("full_fixed_code_or_patch", "").strip()
        
        if target_file and fixed_code and not fixed_code.startswith("# Nội dung"):
            full_path = os.path.join(settings.BASE_DIR, target_file)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(fixed_code)
                    logger.info(f"✨ [Vibercode Auto-Heal] Đã vá thành công file: {target_file}")
                    return True
                except Exception as ex:
                    logger.error(f"❌ [Vibercode Write Error] Không thể ghi đè file: {str(ex)}")

        logger.info("🛡️ [Vibercode Patcher] Đã hoàn tất phân tích chẩn đoán an toàn.")
        return True