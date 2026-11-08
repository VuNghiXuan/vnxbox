# File path: knowledge/agents/viber_test_generator.py
# Chú thích: Viber Test Case Generator - Chuyên gia AI tự động sinh kịch bản test chi tiết dưới dạng bảng Markdown tuân thủ nghiêm ngặt quy chuẩn định dạng vnxBox Enterprise.

import logging
import json
from typing import Dict, Any, List
from django.conf import settings
from ..llm_client import query_local_llm

logger = logging.getLogger(__name__)


class ViberTestGenerator:
    """
    Module chuyên gia sinh test case tự động:
    Chuyển đổi các đặc tả tính năng thành bộ test case chi tiết, 
    bảo đảm định dạng Markdown table với tên nút, trường dữ liệu viết hoa và in đậm trong dấu nháy đôi.
    """

    @classmethod
    def generate_detailed_test_cases(cls, feature_title: str, feature_specification: str) -> str:
        """
        Sử dụng LLM local (qwen2.5-coder) để sinh bảng test case chuyên sâu dựa trên đặc tả.
        """
        logger.info(f"🧪 [Viber Test Generator] Đang sinh test case chuyên sâu cho tính năng: {feature_title}...")

        prompt = f"""
Bạn là Senior QA Test Lead của tập đoàn vnxBox Enterprise.
Dựa vào đặc tả kỹ thuật sau:
- Tính năng: {feature_title}
- Chi tiết: {feature_specification}

NHIỆM VỤ:
Lập một danh sách các kịch bản kiểm thử (Test Cases) chi tiết bao gồm: STT, Tên Test Case, Dữ liệu đầu vào, Các bước thực thi, Kết quả mong đợi.
QUY TẮC BẮT BUỘC:
1. Xuất kết quả dưới dạng bảng Markdown chuẩn.
2. Tất cả tên trường dữ liệu, tên nút bấm (button), và các bước duyệt/thao tác giao diện phải được đặt trong **dấu nháy đôi**, **viết hoa hoàn toàn** và **in đậm** (Ví dụ: **"LƯU"**, **"XÁC NHẬN"**, **"MÃ SẢN PHẨM"**).
3. Kèm theo một khối mã nguồn (Code block) chứa định dạng bảng để dễ dàng sao chép (Copy).
"""
        res = query_local_llm(prompt, task_type="text")
        test_markdown = res.get("response", "Không thể sinh test case.")

        logger.info(f"✅ [Viber Test Generator Success] Đã hoàn thành sinh bộ test case cho: {feature_title}")
        return test_markdown