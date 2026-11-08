# File path: knowledge/agents/agent_factory.py
# Chú thích: Xưởng chế tạo nhân viên AI tự động (Dynamic Agent Factory) cho vnxBox Enterprise.
# Đảm nhiệm việc tự động sinh Công ty (CompanyDomain), Phòng ban và Nhân viên chuyên trách (DepartmentRegistry) 
# khi hệ thống nạp tài liệu mới, gắn chặt trách nhiệm, KPI chống nhẩm số và quy tắc phối hợp liên phòng ban.

import logging
import json
from typing import Dict, Any
from ..models import CompanyDomain, DepartmentRegistry
from ..llm_client import query_local_llm

logger = logging.getLogger(__name__)


class DynamicAgentFactory:
    """
    Xưởng chế tạo nhân viên AI tập đoàn (Dynamic Agent Factory):
    Tự động khởi tạo công ty/lĩnh vực, phòng ban, nhân viên chuyên trách và gán System Prompt 
    ràng buộc trách nhiệm dựa trên nội dung tri thức thực tế được nạp vào.
    """

    @classmethod
    def spawn_or_get_specialist(cls, company_code: str, company_name: str, sub_field: str, sample_snippet: str = "") -> DepartmentRegistry:
        """
        Kiểm tra hệ thống tập đoàn:
        1. Đảm bảo CompanyDomain đã tồn tại (nếu chưa, tự sinh mới).
        2. Kiểm tra nhân viên chuyên trách (DepartmentRegistry) cho nghiệp vụ sub_field. 
        Nếu chưa có, tự động 'tuyển dụng' và thiết kế System Prompt ràng buộc pháp lý/nghiệp vụ.
        """
        clean_comp_code = company_code.upper().strip().replace(" ", "_").replace("&", "AND")
        clean_sub = sub_field.upper().strip().replace(" ", "_") if sub_field else "GENERAL_OPS"
        agent_name = f"Specialist_{clean_comp_code}_{clean_sub}"

        # 1. Đảm bảo Công ty / Lĩnh vực tồn tại trong tập đoàn
        company_obj, _ = CompanyDomain.objects.get_or_create(
            company_code=clean_comp_code,
            defaults={
                "company_name": company_name or f"Công ty / Lĩnh vực {company_code}",
                "description": f"Danh nghĩa hoạt động chuyên ngành cho {company_code}",
                "is_active": True
            }
        )

        # 2. Truy vấn xem nhân viên chuyên trách đã tồn tại chưa
        existing_agent = DepartmentRegistry.objects.filter(
            company=company_obj,
            agent_name=agent_name
        ).first()

        if existing_agent:
            return existing_agent

        # 3. Nếu chưa có, dùng LLM thiết kế System Prompt gắn trách nhiệm đặc thù
        architect_prompt = f"""
Bạn là Trưởng ban Nhân sự Tập đoàn AI vnxBox Enterprise.
Hãy thiết kế một System Prompt nghiêm ngặt cho một Chuyên viên AI (Sub-Agent) vừa được 'tuyển dụng' để quản lý một công ty hoặc lĩnh vực nghiệp vụ mới gia nhập tập đoàn.

THÔNG TIN PHÂN CÔNG:
- Công ty / Lĩnh vực lớn: 
{company_obj.company_name} ({clean_comp_code})
- Nghiệp vụ chuyên môn chi tiết: 
{sub_field or 'Nghiệp vụ tổng hợp'}
- Mẫu tài liệu/dữ liệu thực tế: 
{sample_snippet[:400]}

YÊU CẦU ĐẦU RA (JSON thuần túy, không markdown):
{{
  "role_description": "Mô tả rõ chức năng nhiệm vụ của nhân viên này trong tập đoàn",
  "responsibilities": "Liệt kê rõ các trách nhiệm chính như rà soát quy chế, tính toán định mức, dự toán hoặc hạch toán chính xác.",
  "kpi_rules": "Ràng buộc kỹ thuật khắt khe: Cấm nhẩm số, Cấm cắt xén điều khoản văn bản, Bắt buộc dùng Secure Sandbox cho mọi tính toán.",
  "system_prompt": "System prompt chi tiết định hình tư duy và quy tắc làm việc chuyên sâu."
}}
"""
        
        fallback_desc = f"Chuyên viên AI độc quyền phụ trách lĩnh vực {company_obj.company_name} - {sub_field or 'Tổng hợp'}"
        fallback_resp = "Quản lý quy chế, rà soát văn bản và tính toán định mức/chi phí chính xác."
        fallback_kpi = "1. Tuyệt đối không cắt xén điều khoản nguyên thủy. 2. Cấm nhẩm số, mọi tính toán phải qua Secure Sandbox."
        fallback_prompt = (
            f"Bạn là Chuyên viên AI thuộc hệ sinh thái tập đoàn, đại diện cho công ty/lĩnh vực: {company_obj.company_name}.\n"
            f"Nghiệp vụ chuyên sâu: {sub_field or 'Quản lý toàn bộ định mức và quy chế lĩnh vực này'}.\n"
            "QUY TẮC RÀNG BUỘC TRÁCH NHIỆM:\n"
            "1. TUYỆT ĐỐI KHÔNG cắt xén, tóm tắt cục bộ các điều khoản nguyên thủy (Anti-Truncation Rule).\n"
            "2. CẤM NHẨM SỐ VÀ CẤM HARDCODE. Mọi bài toán tính toán chi phí, định mức, dự toán hay số liệu tài chính phải được viết mã Python trong ```python ... ``` để Secure Sandbox thực thi chính xác 100%.\n"
            "3. Sẵn sàng phối hợp, tiếp nhận công việc hỗ trợ chéo từ các phòng ban/công ty khác trong tập đoàn khi Ban Giám Đốc điều phối."
        )

        try:
            res = query_local_llm(architect_prompt, system_prompt="AI Corporate Architect", task_type="general")
            if res.get("success"):
                raw_resp = res["response"].replace("```json", "").replace("```", "").strip()
                parsed = json.loads(raw_resp)
                role_desc = parsed.get("role_description", fallback_desc)
                responsibilities = parsed.get("responsibilities", fallback_resp)
                kpi_rules = parsed.get("kpi_rules", fallback_kpi)
                sys_prompt = parsed.get("system_prompt", fallback_prompt)
            else:
                role_desc, responsibilities, kpi_rules, sys_prompt = fallback_desc, fallback_resp, fallback_kpi, fallback_prompt
        except Exception as err:
            logger.warning(f"Lỗi khi tự sinh agent qua factory: {str(err)}")
            role_desc, responsibilities, kpi_rules, sys_prompt = fallback_desc, fallback_resp, fallback_kpi, fallback_prompt

        # 4. Đăng ký nhân viên mới vào bảng DepartmentRegistry của tập đoàn kèm theo nhiệm vụ & KPI
        new_specialist = DepartmentRegistry.objects.create(
            company=company_obj,
            department_code=clean_comp_code,
            agent_name=agent_name,
            role_description=role_desc,
            responsibilities=responsibilities,
            kpi_rules=kpi_rules,
            system_prompt=sys_prompt,
            required_tools=["Secure_Sandbox", "Deep_Traceability", "Cross_Department_Support"],
            is_active=True
        )

        logger.info(f"🏢 [Corporate Agent Factory] Tập đoàn vừa tự sinh thành công công ty [{clean_comp_code}], phòng ban và nhân viên [{agent_name}]!")
        return new_specialist