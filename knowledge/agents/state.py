# File path: knowledge/agents/state.py
# Chú thích: Định nghĩa cấu trúc Trạng thái (AgentState) cho LangGraph Multi-Agent Orchestrator.
# Quản lý toàn bộ luồng dữ liệu truyền qua lại giữa các nút: Ingestion, Router, BA Arbiter, Sandbox và QA Evaluator.

from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """
    State định nghĩa ngữ cảnh và dữ liệu chạy xuyên suốt trong đồ thị LangGraph.
    """
    session_id: Optional[str]
    user_query: str
    domain_name: Optional[str]
    sub_domain: Optional[str]
    
    # Dữ liệu tài liệu & trích dẫn retrieved từ Hybrid Search
    retrieved_chunks: List[Dict[str, Any]]
    combined_context: str
    citations: List[Dict[str, Any]]
    
    # Định danh nhân viên / phòng ban chuyên trách (Dynamic Agent Factory)
    assigned_agent_name: Optional[str]
    department_code: Optional[str]
    
    # Kết quả qua phòng Trọng tài BA Debate
    draft_response: Optional[str]
    critic_feedback: Optional[str]
    is_conflict_detected: bool
    final_debated_answer: Optional[str]
    
    # Kết quả thực thi từ Secure Sandbox (nếu có tính toán số học/vàng bạc)
    sandbox_code: Optional[str]
    sandbox_execution_result: Optional[Dict[str, Any]]
    
    # Kết quả kiểm định từ Phòng QA & RAGAS Evaluator
    qa_score: float
    faithfulness_score: float
    relevance_score: float
    qa_passed: bool
    
    # Đầu ra cuối cùng chuẩn bị trả về User / Chat Workspace
    final_output: Optional[str]
    error_message: Optional[str]