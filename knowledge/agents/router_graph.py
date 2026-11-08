# File path: knowledge/agents/router_graph.py
# Chú thích: LangGraph Multi-Role Orchestrator (Ban Giám Đốc Tập đoàn AI vnxBox Enterprise).
# Đảm nhiệm điều phối luồng: Nhận diện lĩnh vực/công ty ➔ Kích hoạt/Truy xuất Agent qua Dynamic Factory 
# ➔ Phòng Trọng tài BA Debate ➔ Neuro-Symbolic Sandbox ➔ QA Evaluator.

import logging
import re
from typing import Dict, Any

from .agent_factory import DynamicAgentFactory
from .ba_arbiter import BAArbiterEngine
from .qa_evaluator import QAEvaluatorEngine
from ..sandbox import run_secure_sandbox
from ..search_engine import hybrid_search

logger = logging.getLogger(__name__)


class LangGraphOrchestrator:
    """
    Ban Giám Đốc Tập đoàn AI (LangGraph Router Controller):
    Điều phối thông minh các phòng ban, công ty con và chuyên viên AI tự sinh trong hệ sinh thái.
    """

    @classmethod
    def process_corporate_pipeline(cls, user_query: str, domain_name: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Thực thi luồng vận hành tự động toàn tập đoàn:
        1. Quét tìm kiếm tri thức phù hợp từ các công ty/lĩnh vực trong hệ thống.
        2. Tự động 'gọi tên' hoặc 'tuyển dụng' nhân sự chuyên trách thông qua DynamicAgentFactory với định danh chuẩn.
        3. Phối hợp liên phòng ban qua BA Arbiter và Secure Sandbox.
        """
        logger.info(f"🏢 [Ban Giám Đốc Tập đoàn] Tiếp nhận yêu cầu: '{user_query[:50]}...'")

        # 1. Truy vấn Tri thức qua Hybrid Search
        search_res = hybrid_search(user_query, domain_name=domain_name, limit=3)
        
        if not search_res.get("success", False):
            refusal_msg = search_res.get("message", "Hệ thống tập đoàn chưa ghi nhận quy chế hoặc dữ liệu về lĩnh vực này.")
            return {
                "success": True,
                "refusal": True,
                "answer": refusal_msg,
                "citations": [],
                "sandbox_execution": None,
                "qa_score": 9.0
            }

        # 2. Tổng hợp ngữ cảnh và bóc tách định danh Chapter / ID / Công ty thực tế từ kết quả tìm kiếm
        context_blocks = []
        citations = []
        target_company_code = "GENERAL"
        target_domain = domain_name or "Quy định chung"
        target_sub_domain = "Nghiệp vụ chi tiết"

        for item in search_res.get("results", []):
            target_company_code = item.get("company_code", target_company_code)
            target_domain = item.get("domain_name", target_domain)
            target_sub_domain = item.get("sub_domain", target_sub_domain)
            
            chapter_id = item.get("chapter_id")
            source_file = item.get("source_file", "Tài liệu nội bộ")
            
            hierarchy_path = f"[{target_domain}] > {target_sub_domain}"
            if item.get('chapter_code'):
                hierarchy_path += f" > {item.get('chapter_code')}"
            if item.get('article_code'):
                hierarchy_path += f" > {item.get('article_code')}"
                
            context_blocks.append(
                f"=== [CĂN CỨ TỪ CHAPTER ID: {chapter_id} | FILE: {source_file} | PHÂN HỆ: {hierarchy_path}] ===\n{item.get('content')}"
            )
            citations.append({
                "chapter_id": chapter_id,
                "company_code": target_company_code,
                "domain_name": target_domain,
                "sub_domain": target_sub_domain,
                "location": hierarchy_path,
                "title": item.get("title"),
                "source_file": source_file
            })

        combined_context = "\n\n".join(context_blocks)

        # 3. Kích hoạt Dynamic Agent Factory đúng tham số: Truyền đúng company_code và sub_field để gắn kết nhân sự AI chính xác
        specialist_agent = DynamicAgentFactory.spawn_or_get_specialist(
            company_code=target_company_code,
            company_name=f"Tập đoàn vnxBox ({target_company_code})",
            sub_field=target_sub_domain,
            sample_snippet=combined_context[:400]
        )
        logger.info(f"👔 [Điều phối Tập đoàn] Giao việc cho chuyên viên: [{specialist_agent.department_code}] {specialist_agent.agent_name}")

        # 4. Kích hoạt Phòng Trọng tài BA & Tranh biện ngầm (< 1s)
        debate_res = BAArbiterEngine.execute_debate_pipeline(
            question=user_query,
            context_str=combined_context,
            domain_name=f"{target_domain} - {specialist_agent.agent_name}"
        )
        raw_answer = debate_res["final_answer"]

        # 5. Neuro-Symbolic Sandbox Execution (Chạy code Python tính toán định mức, dự toán, tài chính chính xác tuyệt đối)
        sandbox_result = None
        final_answer = raw_answer
        python_code_blocks = re.findall(r"```python\s*(.*?)\s*```", raw_answer, re.DOTALL)

        if python_code_blocks:
            target_code = python_code_blocks[0].strip()
            sandbox_result = run_secure_sandbox(code_str=target_code, timeout_seconds=3)
            if sandbox_result and sandbox_result.get("success"):
                final_answer += f"\n\n**🧮 Kết quả tính toán chuyên sâu từ Secure Sandbox (Zero-Hallucination):**\n{sandbox_result.get('output', '')}"

        # 6. Kiểm định chất lượng từ Phòng QA & RAGAS Evaluator
        qa_eval = QAEvaluatorEngine.evaluate_response_quality(
            question=user_query,
            answer=final_answer,
            citations=citations
        )

        if not qa_eval["passed"]:
            logger.warning(f"⚠️ [Phòng QA Tập đoàn] Điểm chất lượng thấp ({qa_eval['qa_score']}/10). Chuyển phiếu kiểm duyệt cho Admin.")
            final_answer = "Bản trả lời chưa đạt chỉ số tin cậy QA của tập đoàn (Score < 8.5). Đã chuyển phiếu xử lý cho Quản lý kiểm duyệt."

        return {
            "success": True,
            "refusal": False,
            "department_code": specialist_agent.department_code,
            "assigned_agent": specialist_agent.agent_name,
            "answer": final_answer,
            "citations": citations,
            "sandbox_execution": sandbox_result,
            "qa_score": qa_eval["qa_score"]
        }