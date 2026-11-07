# File path: knowledge/ai_services.py
# Chú thích: Engine tích hợp AI Service trung tâm cho vnxBox Enterprise (Build 2026).
# Tích hợp Hardware Auto-Profiling (Khảo sát RAM/GPU/CPU), Multi-Model Routing, 
# Hardware Adaptive Chunking Config, và Safe FAQ Ingestion triệt tiêu ReadTimeoutError.

import json
import logging
import requests
import re
import os
import psutil
from .sandbox import run_secure_sandbox
from .models import KnowledgeChapter, KnowledgeFAQ, ChatSession, ChatMessage

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL_NAME = "qwen2.5-coder"  # Hoặc "qwen2.5-coder" tùy theo model sếp đang cài trên Ollama

# =====================================================================
# 1. HARDWARE AUTO-PROFILING & ADAPTIVE CONFIGURATION ENGINE
# =====================================================================
def profile_client_hardware() -> dict:
    """
    Tự động quét thông số phần cứng máy khách (RAM, GPU VRAM, CPU)
    để phân loại nhóm cấu hình và trả về chiến lược vận hành tối ưu.
    """
    try:
        # Lấy thông số System RAM
        mem_info = psutil.virtual_memory()
        total_ram_gb = round(mem_info.total / (1024 ** 3), 2)

        # Kiểm tra GPU / VRAM (NVIDIA GPU via PyTorch hoặc CUDA nvml nếu có)
        has_gpu = False
        vram_gb = 0.0
        try:
            import torch
            if torch.cuda.is_available():
                has_gpu = True
                vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
        except Exception:
            pass

        # Phân loại 3 tầng phần cứng (High-End, Mid-Range, Low-End)
        if (has_gpu and vram_gb >= 8.0) or total_ram_gb >= 32.0:
            profile_tier = "High-End"
            model_name = "qwen2.5-coder:14b" if has_gpu else "qwen2.5-coder:7b"
            num_ctx = 16384
            request_timeout = 600  # 10 phút chống timeout với tài liệu cực lớn
            chunk_size = 1200
            chunk_overlap = 200
        elif (has_gpu and vram_gb >= 4.0) or total_ram_gb >= 16.0:
            profile_tier = "Mid-Range"
            model_name = "qwen2.5-coder:7b"
            num_ctx = 8192
            request_timeout = 450
            chunk_size = 700
            chunk_overlap = 100
        else:
            profile_tier = "Low-End"
            # Máy CPU yếu hoặc RAM <= 8GB: Chuyển model nhẹ, bóp ngắn Context Window để chống treo
            model_name = "qwen2.5:1.5b"
            num_ctx = 4096
            request_timeout = 300
            chunk_size = 400
            chunk_overlap = 50

        return {
            "tier": profile_tier,
            "total_ram_gb": total_ram_gb,
            "has_gpu": has_gpu,
            "vram_gb": vram_gb,
            "recommended_model": model_name,
            "num_ctx": num_ctx,
            "request_timeout": request_timeout,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        }
    except Exception as err:
        logger.warning(f"Lỗi khi quét phần cứng máy khách: {str(err)}. Áp dụng cấu hình mặc định Mid-Range.")
        return {
            "tier": "Mid-Range",
            "total_ram_gb": 16.0,
            "has_gpu": False,
            "vram_gb": 0.0,
            "recommended_model": "qwen2.5-coder:7b",
            "num_ctx": 8192,
            "request_timeout": 450,
            "chunk_size": 700,
            "chunk_overlap": 100
        }


def get_hardware_adaptive_chunk_config() -> dict:
    """Trả về cấu hình Chunking tối ưu cho module file_parsers và chunker."""
    hw_info = profile_client_hardware()
    return {
        "chunk_size": hw_info["chunk_size"],
        "chunk_overlap": hw_info["chunk_overlap"],
        "profile_tier": hw_info["tier"]
    }


def query_local_llm(prompt_text: str, system_prompt: str = "", task_type: str = "code") -> dict:
    """
    Gửi request tới Ollama Local LLM với cơ chế Hardware Adaptive & Multi-Model Routing:
    - task_type='code': Ưu tiên mô hình lập trình & toán (qwen2.5-coder)
    - task_type='general': Ưu tiên mô hình tổng hợp văn bản
    - task_type='summary': Dùng mô hình nhẹ xử lý nhanh bộ nhớ hội thoại
    """
    hw_config = profile_client_hardware()
    
    # Định tuyến Mô hình Chuyên biệt (Multi-Model Routing)
    selected_model = hw_config["recommended_model"]
    if task_type == "summary" and hw_config["tier"] != "High-End":
        selected_model = "qwen2.5:1.5b"  # Model siêu nhẹ cho tóm tắt lịch sử chat

    payload = {
        "model": selected_model,
        "prompt": prompt_text,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Nhiệt độ thấp đảm bảo chính xác dữ liệu & JSON
            "num_ctx": hw_config["num_ctx"],
            "num_predict": 1536
        }
    }
    
    timeout_val = hw_config["request_timeout"]
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout_val)
        if response.status_code == 200:
            return {"success": True, "response": response.json().get("response", "").strip()}
        else:
            logger.error(f"Ollama API Error Status: {response.status_code}")
            return {"success": False, "error": f"Lỗi từ Ollama API: Status {response.status_code}"}
    except requests.exceptions.ReadTimeout:
        logger.error(f"ReadTimeoutError: Ollama quá thời gian xử lý ({timeout_val}s).")
        return {"success": False, "error": f"Mô hình AI xử lý quá thời gian quy định ({timeout_val}s). Vui lòng chia nhỏ tài liệu."}
    except Exception as e:
        logger.error(f"Không thể kết nối Ollama API: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Không thể kết nối tới Ollama local: {str(e)}"}


def _clean_json_response(raw_text: str) -> str:
    """Làm sạch chuỗi JSON trả về từ LLM (loại bỏ markdown codeblocks)."""
    if not raw_text:
        return "{}"
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    return cleaned


def _extract_faq_string(faq_item) -> str:
    """
    HÀM AN TOÀN TRÁCH LỖI 'dict object has no attribute strip':
    Chuyển đổi mọi định dạng FAQ (string, dict, object) thành chuỗi thuần túy.
    """
    if not faq_item:
        return ""
    if isinstance(faq_item, str):
        return faq_item.strip()
    if isinstance(faq_item, dict):
        return str(faq_item.get("question_variation") or faq_item.get("question") or faq_item.get("text") or "").strip()
    return str(faq_item).strip()


# =====================================================================
# 2. DYNAMIC DOMAIN PROMPT ROUTER
# =====================================================================
def get_domain_specific_system_prompt(domain_name: str, question: str) -> str:
    """Tự động phân tích và trả về System Prompt chuyên biệt cho từng nghiệp vụ."""
    q_lower = question.lower()
    
    # 1. NGHIỆP VỤ VÀNG, TRANG SỨC & TÍNH TOÁN QUY ĐỔI
    if any(k in q_lower for k in ["vàng", "9999", "980", "750", "610", "chỉ", "lượng", "cây", "thu đổi", "đổi vàng", "hao hụt"]):
        return (
            "Bạn là Chuyên gia Kế toán & Nghiệp vụ Thu đổi Vàng Bạc Trang Sức Cấp cao của doanh nghiệp.\n"
            "QUY TẮC NGHIỆP VỤ QUY ĐỔI VÀNG BẮT BUỘC (TUYỆT ĐỐI KHÔNG SAI LỆCH):\n"
            "1. Vàng 9999 = 10 tuổi (100%), Vàng 980 = 9.8 tuổi (98%).\n"
            "2. BẢO TOÀN GIÁ TRỊ TÀI SẢN: Đổi từ vàng tuổi cao (9999) sang vàng tuổi thấp (980) thì SỐ CHỈ VÀNG 980 NHẬN VỀ PHẢI NHIỀU HƠN số chỉ 9999 giao vào, HOẶC cửa hàng phải hoàn tiền thừa cho khách.\n"
            "3. TUYỆT ĐỐI KHÔNG được tính giảm số chỉ vàng hoặc bắt khách vừa mất thêm vàng vừa phải bù tiền.\n"
            "4. Viết code Python trong ```python ... ``` để Secure Sandbox thực thi toán học ngầm.\n"
            "5. ĐỊNH DẠNG TRÌNH BÀY:\n"
            "   - **Căn cứ tài liệu / Quy chế nội bộ**\n"
            "   - **Phân tích chi tiết từng bước (1., 2., 3...)**\n"
            "   - **Kết quả quy đổi số chỉ & bù trừ tiền mặt rõ ràng.**"
        )

    # 2. NGHIỆP VỤ XÂY DỰNG & ĐẦU TƯ
    elif any(k in q_lower for k in ["xây dựng", "thi công", "nghiệm thu", "hợp đồng", "chủ đầu tư", "nhà thầu"]):
        return (
            "Bạn là Chuyên gia Pháp lý & Quản lý Dự án Đầu tư Xây dựng vnxBox.\n"
            "Nêu rõ Điều, Khoản luật định, phân định trách nhiệm Chủ đầu tư vs Nhà thầu, gạch đầu dòng rõ ràng."
        )

    return (
        "Bạn là Trợ lý AI Chuyên gia Quản trị Doanh nghiệp vnxBox Enterprise.\n"
        "Hãy trả lời chính xác dựa trên Ngữ cảnh Tài liệu Nội bộ. Nếu có tính toán, bắt buộc dùng mã Python trong ```python ... ```."
    )


def format_sandbox_result_to_vietnamese(raw_question: str, raw_code: str, sandbox_output: str) -> str:
    """Natural Language Sandbox Formatter chuẩn hóa định dạng số Việt Nam."""
    formatter_prompt = f"""
Bạn là chuyên gia tài chính nghiệp vụ. Kết quả từ Secure Sandbox:

CÂU HỎI GỐC: {raw_question}
KẾT QUẢ THÔ TỪ SANDBOX:
{sandbox_output}

NHIỆM VỤ:
Diễn giải thành Tiếng Việt ngắn gọn, chuyên nghiệp:
- Tiền mặt: Dùng dấu chấm (.) phân cách hàng nghìn (VD: 1.500.000 VNĐ).
- Trọng lượng vàng: Dùng dấu phẩy (,) cho phần thập phân (VD: 5,102 chỉ).
- Chỉ rõ Cửa hàng thối lại tiền hay Khách bù thêm.
- KHÔNG nhắc tên biến Python hay chữ Sandbox.
"""
    res = query_local_llm(formatter_prompt, system_prompt="Bạn là trợ lý diễn giải số liệu chính xác theo chuẩn Việt Nam.", task_type="general")
    if res.get("success"):
        return res.get("response", "")
    return f"Kết quả tính toán chi tiết: {sandbox_output}"


# =====================================================================
# 3. CHAT QUERY PROCESSOR & CONTEXT CITATION
# =====================================================================
def process_chat_query(question: str, domain_name: str = None, session_id: str = None) -> dict:
    """Xử lý truy vấn chat nâng cao tích hợp Domain Routing & Context Citation."""
    from .search_engine import hybrid_search

    chat_session = None
    history_context_str = ""
    
    if session_id:
        chat_session, _ = ChatSession.objects.get_or_create(session_id=session_id)
        recent_messages = chat_session.messages.order_by('-created_at')[:8]
        recent_messages = reversed(list(recent_messages))
        
        history_blocks = [f"{'Người dùng' if m.sender == 'user' else 'Trợ lý AI'}: {m.text}" for m in recent_messages]
        if history_blocks:
            history_context_str = "\n".join(history_blocks)

        ChatMessage.objects.create(session=chat_session, sender="user", text=question)

    search_res = hybrid_search(question, domain_name=domain_name, limit=3)
    
    if not search_res.get("success", False):
        refusal_msg = search_res.get("message", "Kho tri thức nội bộ chưa ghi nhận dữ liệu về quy định này.")
        if chat_session:
            ChatMessage.objects.create(session=chat_session, sender="ai", text=refusal_msg)
        return {
            "success": True,
            "refusal": True,
            "session_id": str(chat_session.session_id) if chat_session else None,
            "answer": refusal_msg,
            "citations": [],
            "sandbox_execution": None
        }
    
    context_blocks = []
    citations = []
    for item in search_res.get("results", []):
        source_label = f"Tài liệu: {item.get('source_file', 'Văn bản nội bộ')}" + (f" (Sheet: {item.get('sheet_name')})" if item.get('sheet_name') else "")
        hierarchy_path = f"{item.get('domain_name')} > {item.get('sub_domain', 'Chung')}"
        if item.get('chapter_code'):
            hierarchy_path += f" > {item.get('chapter_code')}"
        if item.get('article_code'):
            hierarchy_path += f" > {item.get('article_code')}"
            
        context_blocks.append(
            f"=== [CĂN CỨ TÀI LIỆU: {item.get('title')} | Phân cấp: {hierarchy_path} | Nguồn: {source_label}] ===\n"
            f"{item.get('content')}"
        )
        citations.append({
            "chapter_id": item.get("chapter_id"),
            "domain_name": item.get("domain_name"),
            "sub_domain": item.get("sub_domain"),
            "location": hierarchy_path,
            "title": item.get("title"),
            "source_file": item.get("source_file")
        })
        
    combined_context = "\n\n".join(context_blocks)
    system_prompt = get_domain_specific_system_prompt(domain_name or "", question)
    
    prompt = f"""
[LỊCH SỬ HỘI THOẠI]:
{history_context_str if history_context_str else "Chưa có lịch sử."}

[NGỮ CẢNH CĂN CỨ TÀI LIỆU NỘI BỘ]:
{combined_context}

[CÂU HỎI CẦN XỬ LÝ]: {question}

HƯỚNG DẪN TRÌNH BÀY:
1. Nêu rõ Căn cứ tài liệu / Quy định trích dẫn từ Ngữ cảnh.
2. Trình trình chi tiết phân dòng từng bước (1., 2., 3.).
3. Nếu có tính toán, viết mã Python bọc trong ```python ... ``` để Sandbox tính toán chính xác.
"""
    
    llm_res = query_local_llm(prompt, system_prompt, task_type="code")
    if not llm_res.get("success"):
        return {"success": False, "error": llm_res.get("error")}
        
    raw_ai_response = llm_res.get("response", "")
    
    sandbox_execution_result = None
    python_code_blocks = re.findall(r"```python\s*(.*?)\s*```", raw_ai_response, re.DOTALL)
    clean_ai_response = re.sub(r"```python\s*.*?\s*```", "", raw_ai_response, flags=re.DOTALL).strip()
    
    if python_code_blocks:
        target_code = python_code_blocks[0].strip()
        sandbox_execution_result = run_secure_sandbox(code_str=target_code, timeout_seconds=3)
        
        if sandbox_execution_result and sandbox_execution_result.get("success"):
            raw_output = sandbox_execution_result.get("output", "")
            vietnamese_summary = format_sandbox_result_to_vietnamese(question, target_code, raw_output)
            sandbox_execution_result["formatted_vietnamese_summary"] = vietnamese_summary
            
            if clean_ai_response:
                clean_ai_response += f"\n\n**🧮 Diễn giải chi tiết tính toán:**\n{vietnamese_summary}"
            else:
                clean_ai_response = vietnamese_summary

    if chat_session:
        ChatMessage.objects.create(
            session=chat_session, 
            sender="ai", 
            text=clean_ai_response,
            metadata={"citations": citations, "sandbox": sandbox_execution_result}
        )

    return {
        "success": True,
        "refusal": False,
        "session_id": str(chat_session.session_id) if chat_session else None,
        "answer": clean_ai_response,
        "citations": citations,
        "sandbox_execution": sandbox_execution_result
    }


# =====================================================================
# 4. DEEP HIERARCHICAL EXTRACTION & FAQ RADAR GENERATOR
# =====================================================================
def analyze_and_extract_metadata(raw_chunk_text: str, default_domain: str = "Quy định chung") -> dict:
    """
    AI tự động trích xuất ĐA TẦNG (Lĩnh vực -> Nghiệp vụ -> Chương -> Điều)
    và sinh bộ câu hỏi FAQ Radar mở rộng từ 6 đến 10 câu hỏi bao phủ mọi góc độ.
    """
    system_instruction = (
        "Bạn là hệ thống AI trích xuất cấu trúc tri thức doanh nghiệp đa tầng. "
        "Trả về kết quả JSON thuần túy, KHÔNG có markdown ```json bên ngoài."
    )
    
    prompt = f"""
Hãy phân tích đoạn văn bản dưới đây và trích xuất cấu trúc phân cấp (Cha - Con - Cháu - Chắt) cùng bộ câu hỏi mẫu:

VĂN BẢN:
---
{raw_chunk_text[:4000]}
---

YÊU CẦU ĐẦU RA JSON ĐÚNG CẤU TRÚC:
{{
  "domain_name": "{default_domain}",
  "sub_domain": "Tên nghiệp vụ cụ thể (Ví dụ: Quy định mua bán / Quản lý thi công / Hợp đồng)",
  "chapter_code": "Chương I (hoặc Mã Phần/Mục nếu có)",
  "article_code": "Điều 1 (hoặc Mã Tiết/Khoản nếu có)",
  "title": "Tiêu đề ngắn gọn phản ánh đúng nội dung chính",
  "summary": "Tóm tắt súc tích nội dung văn bản",
  "faq_variations": [
    "Câu hỏi về khái niệm/điều kiện áp dụng?",
    "Câu hỏi về công thức/cách tính toán số liệu?",
    "Câu hỏi về tỷ lệ hao hụt/định mức/biểu phí?",
    "Câu hỏi về quy trình thực hiện các bước?",
    "Câu hỏi về trách nhiệm hoặc các ngoại lệ?",
    "Câu hỏi về cách bù trừ/hoàn tiền nếu có phát sinh?"
  ]
}}
"""
    result = query_local_llm(prompt, system_instruction, task_type="general")
    if result.get("success"):
        try:
            clean_str = _clean_json_response(result["response"])
            data = json.loads(clean_str)
            
            # Đảm bảo danh sách FAQ luôn là danh sách các chuỗi sạch
            raw_faqs = data.get("faq_variations", [])
            clean_faqs = []
            for f in raw_faqs:
                f_str = _extract_faq_string(f)
                if f_str:
                    clean_faqs.append(f_str)
                    
            if len(clean_faqs) < 3:
                doc_title = data.get("title", "nội dung này")
                clean_faqs.extend([
                    f"Quy định chi tiết về {doc_title} thực hiện như thế nào?",
                    f"Công thức tính toán và hạn mức áp dụng cho {doc_title} ra sao?",
                    f"Điều kiện và biểu phí liên quan tới {doc_title} gồm những gì?"
                ])
                
            data["faq_variations"] = clean_faqs
            return data
        except Exception as err:
            logger.warning(f"Lỗi khi parse JSON metadata phân cấp: {str(err)}")
            
    # Fallback dự phòng nếu LLM không trả JSON
    return {
        "domain_name": default_domain,
        "sub_domain": "Quy định chung",
        "chapter_code": "Chương I",
        "article_code": "Điều 1",
        "title": raw_chunk_text[:50].strip() + "...",
        "summary": raw_chunk_text[:200],
        "faq_variations": [
            "Nội dung quy định chi tiết trong văn bản này là gì?",
            "Cách thức tính toán số liệu và áp dụng chính sách ra sao?",
            "Quy trình thực hiện nghiệp vụ được quy định cụ thể như thế nào?"
        ]
    }


def process_ingest_document(raw_text: str, domain_name: str = "Quy định chung", scope: str = "Toàn hệ thống") -> dict:
    """Xử lý nạp văn bản thô với trích xuất phân cấp và sinh FAQ an toàn."""
    try:
        meta = analyze_and_extract_metadata(raw_text, default_domain=domain_name)

        chapter = KnowledgeChapter.objects.create(
            title=meta.get("title", "Tài liệu văn bản thô"),
            source_file="Nhập văn bản thô",
            domain_name=meta.get("domain_name", domain_name),
            sub_domain=meta.get("sub_domain", "Quy định chung"),
            chapter_code=meta.get("chapter_code", ""),
            article_code=meta.get("article_code", ""),
            summary=meta.get("summary", ""),
            content=raw_text,
            metadata={"scope": scope},
            status="AUTO_APPROVED"
        )

        for q_item in meta.get("faq_variations", []):
            q_text = _extract_faq_string(q_item)
            if q_text:
                KnowledgeFAQ.objects.create(
                    chapter=chapter,
                    question_variation=q_text
                )

        return {"success": True, "chapter": chapter}
    except Exception as e:
        logger.error(f"Lỗi process_ingest_document: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Lỗi lưu tài liệu thô: {str(e)}"}


def process_ingest_file(file_obj, domain_name: str = "Quy định chung", scope: str = "Toàn hệ thống") -> dict:
    """
    Xử lý nạp file (Excel, Word, PDF...) an toàn 100%,
    triệt tiêu hoàn toàn lỗi 'dict object has no attribute strip'.
    """
    from .file_parsers import parse_uploaded_file
    
    parse_result = parse_uploaded_file(file_obj)
    if not parse_result.get("success"):
        return {"success": False, "error": parse_result.get("error")}
        
    chapters_data = parse_result.get("chapters", [])
    if not chapters_data:
        return {"success": False, "error": "Không trích xuất được phân đoạn tri thức nào từ tệp tin."}

    created_chapters = []
    try:
        for ch_data in chapters_data:
            chapter = KnowledgeChapter.objects.create(
                source_file=ch_data.get("source_file"),
                sheet_name=ch_data.get("sheet_name"),
                domain_name=ch_data.get("domain_name", domain_name),
                sub_domain=ch_data.get("sub_domain", "Quy định chung"),
                chapter_code=ch_data.get("chapter_code", ""),
                article_code=ch_data.get("article_code", ""),
                title=ch_data.get("title", "Tài liệu bóc tách"),
                summary=ch_data.get("summary", ""),
                content=ch_data.get("content", ""),
                status="AUTO_APPROVED"
            )

            # Xử lý safe cho danh sách FAQ
            faq_list = ch_data.get("intent_faqs", []) or ch_data.get("faq_variations", [])
            for q_item in faq_list:
                q_text = _extract_faq_string(q_item)
                if q_text:
                    KnowledgeFAQ.objects.create(
                        chapter=chapter,
                        question_variation=q_text
                    )
            created_chapters.append(chapter)

        return {"success": True, "chapter": created_chapters[0] if created_chapters else None}
    
    except Exception as e:
        logger.error(f"Lỗi process_ingest_file: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Lỗi lưu trữ dữ liệu bóc tách: {str(e)}"}