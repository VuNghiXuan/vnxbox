# File path: knowledge/parsers/taxonomy_engine.py
# Chú thích: Cập nhật hàm làm sạch chuỗi JSON thông minh, đảm bảo sinh triệt để câu hỏi FAQ định tuyến.

import logging
import json
import re
from typing import Dict, Any

from ..llm_client import query_local_llm
from ..agents.agent_factory import DynamicAgentFactory

logger = logging.getLogger(__name__)


class TaxonomyEngine:
    """
    Phòng Tiếp Nhận & Ingestion: Phân tích tài liệu thô, gán nhãn định danh đa tầng 
    và tự động kích hoạt Xưởng chế tạo nhân sự (Agent Factory) cho từng công ty/lĩnh vực.
    """

    @staticmethod
    def analyze_and_classify_chunk(raw_chunk_text: str, default_company_code: str = "GENERAL", default_domain: str = "Quy định chung") -> Dict[str, Any]:
        """
        Phân tích đoạn văn bản thô để xác định:
        - Mã công ty / Tập đoàn (company_code, company_name)
        - Lĩnh vực (domain_name) & Nghiệp vụ chi tiết (sub_domain)
        - Cấu trúc Chương, Điều, Tiêu đề và tự động sinh câu hỏi FAQ định tuyến & nhân sự AI.
        """
        system_instruction = (
            "Bạn là hệ thống AI phân loại và trích xuất cấu trúc tri thức doanh nghiệp đa tầng. "
            "Chỉ trả về định dạng JSON thuần túy, tuyệt đối không giải thích gì thêm và không bọc trong markdown code blocks."
        )
        
        prompt = f"""
Hãy phân tích đoạn văn bản dưới đây để gán nhãn taxonomy, xác định công ty/lĩnh vực, cấu trúc và đặc biệt **tự động sinh ra ít nhất 3 đến 5 câu hỏi mẫu định tuyến ý định (Intent Routing FAQs)** mà người dùng thực tế hay tra cứu liên quan đến nội dung này:

VĂN BẢN NỘI BỘ:
---
{raw_chunk_text[:3500]}
---

YÊU CẦU ĐẦU RA JSON TUYỆT ĐỐI (Dùng đúng cấu trúc, không kèm ký tự rác):
{{
  "company_code": "{default_company_code}",
  "company_name": "Tên công ty hoặc tập đoàn phụ trách",
  "domain_name": "{default_domain}",
  "sub_domain": "Tên nghiệp vụ chi tiết",
  "chapter_code": "Chương I (hoặc mã tương đương)",
  "article_code": "Điều 1 (hoặc Mục tương đương)",
  "title": "Tiêu đề ngắn gọn phản ánh đúng nội dung điều khoản",
  "summary": "Tóm tắt súc tích nội dung văn bản",
  "faq_variations": [
    "Câu hỏi mẫu thực tế 1 người dùng hay hỏi?",
    "Câu hỏi mẫu thực tế 2 về quy trình hoặc định mức?",
    "Câu hỏi mẫu thực tế 3 liên quan đến trách nhiệm hoặc quy định?"
  ]
}}
"""
        
        res = query_local_llm(prompt, system_instruction, task_type="general")
        
        # Giá trị mặc định an toàn
        parsed_data = {
            "company_code": default_company_code,
            "company_name": f"Công ty / Lĩnh vực {default_company_code}",
            "domain_name": default_domain,
            "sub_domain": "Quy định chung",
            "chapter_code": "Chương I",
            "article_code": "Điều 1",
            "title": raw_chunk_text[:50].strip() + "...",
            "summary": raw_chunk_text[:200],
            "faq_variations": [
                "Quy định chi tiết trong nội dung này là gì?",
                "Quy trình thực hiện nghiệp vụ này ra sao?",
                "Các điểm lưu ý quan trọng hoặc định mức liên quan là gì?"
            ]
        }

        if res.get("success"):
            raw_response = res["response"]
            try:
                # 1. Thử làm sạch cơ bản
                clean_str = raw_response.replace("```json", "").replace("```", "").strip()
                
                # 2. Dùng regex trích xuất đoạn JSON nếu LLM lỡ kèm chữ thừa bên ngoài
                json_match = re.search(r'\{.*\}', clean_str, re.DOTALL)
                if json_match:
                    clean_str = json_match.group(0)

                data = json.loads(clean_str)
                if isinstance(data, dict):
                    parsed_data.update(data)
            except Exception as err:
                logger.warning(f"Lỗi parse JSON Taxonomy từ LLM: {str(err)} | Raw response: {raw_response[:200]}")

        comp_code = parsed_data.get("company_code", default_company_code)
        comp_name = parsed_data.get("company_name", f"Công ty {comp_code}")
        sub_domain = parsed_data.get("sub_domain", "Quy định chung")

        # 🚀 TỰ ĐỘNG KÍCH HOẠT DYNAMIC AGENT FACTORY (Phòng Nhân sự Tập đoàn):
        assigned_agent = DynamicAgentFactory.spawn_or_get_specialist(
            company_code=comp_code,
            company_name=comp_name,
            sub_field=sub_domain,
            sample_snippet=raw_chunk_text
        )

        parsed_data["assigned_agent_name"] = assigned_agent.agent_name
        parsed_data["department_code"] = assigned_agent.department_code

        return parsed_data