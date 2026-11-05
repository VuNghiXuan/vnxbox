import json
import requests
import re
from .sandbox import run_secure_sandbox
from .models import KnowledgeChapter, KnowledgeFAQ, ChatSession, ChatMessage

# Địa chỉ mặc định của Ollama chạy local trên máy
OLLAMA_API_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL_NAME = "qwen2.5-coder"  # Hoặc model khác anh đang dùng trên Ollama


def query_local_llm(prompt_text, system_prompt=""):
    """
    Gửi request trực tiếp tới Ollama Local LLM đảm bảo bảo mật 100% offline.
    """
    payload = {
        "model": LOCAL_MODEL_NAME,
        "prompt": prompt_text,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Đặt thấp để tăng tính logic, giảm ảo giác
            "num_predict": 1024
        }
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=90)
        if response.status_code == 200:
            return {"success": True, "response": response.json().get("response", "").strip()}
        else:
            return {"success": False, "error": f"Lỗi từ Ollama API: Status {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"Không thể kết nối tới Ollama local: {str(e)}"}


def _clean_json_response(raw_text):
    """Làm sạch chuỗi JSON trả về từ LLM (bọc trong ```json ... ```)"""
    return raw_text.replace("```json", "").replace("```", "").strip()


def analyze_and_extract_metadata(raw_chunk_text, default_domain="Quy định chung"):
    """
    AI tự động phân tích văn bản thô để định vị, tóm tắt và sinh FAQ.
    Được tích hợp cơ chế dự phòng (Fallback) đảm bảo luôn có câu hỏi mẫu.
    """
    system_instruction = (
        "Bạn là hệ thống AI phân tích và phân loại tri thức doanh nghiệp. "
        "Hãy trả về kết quả định dạng JSON thuần túy, KHÔNG có markdown ```json bên ngoài."
    )
    
    prompt = f"""
Phân tích nội dung sau thuộc lĩnh vực: {default_domain}
Nội dung:
---
{raw_chunk_text[:3000]}
---

Trả về ĐÚNG cấu trúc JSON sau:
{{
  "domain_name": "{default_domain}",
  "sub_domain": "Nghiệp vụ chi tiết",
  "chapter_code": "",
  "article_code": "",
  "title": "Tiêu đề ngắn gọn của đoạn văn bản",
  "summary": "Tóm tắt ngắn gọn",
  "faq_variations": [
    "Câu hỏi thực tế 1 về quy định hoặc tính toán trong bài?",
    "Câu hỏi thực tế 2 về định mức hoặc biểu phí?",
    "Câu hỏi thực tế 3 về cách thức thực hiện?"
  ]
}}
"""
    result = query_local_llm(prompt, system_instruction)
    if result["success"]:
        try:
            clean_str = _clean_json_response(result["response"])
            data = json.loads(clean_str)
            
            # Đảm bảo luôn có FAQ, nếu LLM trả về thiếu thì tự gán câu hỏi thông minh
            if not data.get("faq_variations") or len(data["faq_variations"]) == 0:
                doc_title = data.get("title", "tài liệu này")
                data["faq_variations"] = [
                    f"Tra cứu quy định chi tiết về {doc_title} như thế nào?",
                    f"Công thức và cách tính toán áp dụng cho {doc_title} ra sao?",
                    f"Các mức phí, biểu giá hoặc hạn mức quy định cụ thể là gì?"
                ]
            return data
        except Exception:
            pass
            
    # Fallback toàn diện nếu parse JSON lỗi hoàn toàn
    return {
        "domain_name": default_domain,
        "sub_domain": "Quy định chung",
        "chapter_code": "",
        "article_code": "",
        "title": raw_chunk_text[:50].strip() + "...",
        "summary": raw_chunk_text[:200],
        "faq_variations": [
            "Nội dung quy định chi tiết trong tài liệu này là gì?",
            "Cách tính toán số liệu và áp dụng chính sách ra sao?",
            "Quy trình thực hiện nghiệp vụ này được quy định thế nào?"
        ]
    }


def process_ingest_document(raw_text, domain_name="Quy định chung", scope="Toàn hệ thống"):
    """
    Xử lý bóc tách văn bản thô: Lưu KnowledgeChapter và tự động tạo KnowledgeFAQ.
    """
    try:
        meta = analyze_and_extract_metadata(raw_text, default_domain=domain_name)

        chapter = KnowledgeChapter.objects.create(
            title=meta.get("title", "Tài liệu chưa đặt tên"),
            source_file="Nhập văn bản thô",
            domain_name=meta.get("domain_name", domain_name),
            sub_domain=meta.get("sub_domain", "Quy định chung"),
            chapter_code=meta.get("chapter_code", ""),
            article_code=meta.get("article_code", ""),
            summary=meta.get("summary", ""),
            content=raw_text,
            metadata={"scope": scope},  # Lưu phạm vi vào metadata
            status="AUTO_APPROVED"
        )

        faq_list = meta.get("faq_variations", [])
        for q_text in faq_list:
            if q_text and q_text.strip():
                KnowledgeFAQ.objects.create(
                    chapter=chapter,
                    question_variation=q_text.strip()
                )

        return {"success": True, "chapter": chapter}
    except Exception as e:
        return {"success": False, "error": f"Lỗi lưu tài liệu thô & sinh FAQ: {str(e)}"}


def process_ingest_file(file_obj, domain_name="Quy định chung", scope="Toàn hệ thống"):
    """
    Xử lý nạp file thông qua Parser nâng cấp (Hỗ trợ đa Sheet Excel, Word, PDF, Ảnh OCR).
    Lưu từng Chapter/Sheet độc lập và tự động sinh Intent FAQs.
    """
    from .file_parsers import parse_uploaded_file
    
    parse_result = parse_uploaded_file(file_obj)
    if not parse_result["success"]:
        return {"success": False, "error": parse_result["error"]}
    
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
                title=ch_data.get("title", "Tài liệu tự động bóc tách"),
                summary=ch_data.get("summary", ""),
                content=ch_data.get("content", ""),
                status="AUTO_APPROVED"
            )

            faq_list = ch_data.get("intent_faqs", [])
            for q_text in faq_list:
                if q_text and q_text.strip():
                    KnowledgeFAQ.objects.create(
                        chapter=chapter,
                        question_variation=q_text.strip()
                    )
            created_chapters.append(chapter)

        return {"success": True, "chapter": created_chapters[0] if created_chapters else None}
    
    except Exception as e:
        return {"success": False, "error": f"Lỗi lưu trữ dữ liệu bóc tách: {str(e)}"}


def format_sandbox_result_to_vietnamese(raw_question, raw_code, sandbox_output):
    """
    Natural Language Sandbox Formatter:
    Chuyển đổi kết quả JSON/số liệu thô từ Sandbox thành câu trả lời Tiếng Việt mạch lạc.
    """
    formatter_prompt = f"""
Bạn là chuyên gia tài chính và nghiệp vụ doanh nghiệp. Hệ thống vừa thực thi mã tính toán an toàn trong Sandbox và thu được kết quả thô sau:

CÂU HỎI GỐC: {raw_question}
MÃ CODE ĐÃ CHẠY: 
{raw_code}

KẾT QUẢ THÔ TỪ SANDBOX:
{sandbox_output}

NHIỆM VỤ:
Hãy viết lại kết quả thành một đoạn giải thích bằng Tiếng Việt rõ ràng, chuyên nghiệp, lịch sự cho người dùng cuối. 
QUY CHUẨN BẮT BUỘC VỀ ĐỊNH DẠNG SỐ HỌC:
- Đơn vị tiền tệ phải hiển thị rõ ràng có dấu chấm phân cách hàng nghìn kèm chữ (VD: 15.000.000 VNĐ hoặc 3.500.000 đồng).
- Đơn vị trọng lượng (vàng, định mức, khối lượng) phải dùng dấu phẩy cho phần thập phân theo chuẩn Việt Nam (VD: 3,88 chỉ, 6,12 chỉ, 1,25 kg).
- TUYỆT ĐỐI KHÔNG nhắc đến tên biến lập trình hay mã code Python trong câu trả lời.
"""
    res = query_local_llm(formatter_prompt, system_prompt="Bạn là trợ lý AI diễn giải số liệu chính xác tuyệt đối.")
    if res["success"]:
        return res["response"]
    return f"Kết quả tính toán chi tiết: {sandbox_output}"


def process_chat_query(question, domain_name=None, session_id=None):
    """
    Xử lý câu hỏi chat nâng cao:
    1. Quản lý phiên chat và truy vấn Sliding Window Memory (6-10 tin nhắn gần nhất).
    2. Intent Routing & Hybrid Search tìm kiếm tài liệu chuẩn xác.
    3. Thực thi Sandbox nếu có tính toán số học và gọi Formatter chuẩn hóa Tiếng Việt.
    4. Lưu vết lịch sử tin nhắn vào ChatMessage.
    """
    from .search_engine import hybrid_search

    chat_session = None
    history_context_str = ""
    
    if session_id:
        chat_session, _ = ChatSession.objects.get_or_create(session_id=session_id)
        recent_messages = chat_session.messages.order_by('-created_at')[:8]
        recent_messages = reversed(list(recent_messages))
        
        history_blocks = []
        for msg in recent_messages:
            role = "Người dùng" if msg.sender == "user" else "Trợ lý AI"
            history_blocks.append(f"{role}: {msg.text}")
        if history_blocks:
            history_context_str = "\n".join(history_blocks)

        ChatMessage.objects.create(session=chat_session, sender="user", text=question)

    search_res = hybrid_search(question, domain_name=domain_name, limit=3)
    
    if not search_res["success"]:
        refusal_msg = search_res["message"]
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
    for item in search_res["results"]:
        source_label = f"File: {item.get('source_file', 'N/A')}" + (f" | Sheet: {item.get('sheet_name')}" if item.get('sheet_name') else "")
        location_str = f"{item['chapter_code']} > {item['article_code']}" if item['chapter_code'] else "Chung"
        context_blocks.append(
            f"--- [{source_label} | Lĩnh vực: {item['domain_name']} | Vị trí: {location_str}] "
            f"Tiêu đề: {item['title']} ---\n{item['content']}"
        )
        citations.append({
            "chapter_id": item["chapter_id"],
            "domain_name": item["domain_name"],
            "sub_domain": item["sub_domain"],
            "location": location_str,
            "title": item["title"],
            "source_file": item.get("source_file")
        })
        
    combined_context = "\n\n".join(context_blocks)
    
    system_prompt = (
        "Bạn là trợ lý AI doanh nghiệp vnxBox Enterprise. Hãy trả lời câu hỏi dựa TRỰC TIẾP vào ngữ cảnh nội bộ. "
        "Đảm bảo tính chính xác tuyệt đối, trung thực và trích dẫn đúng nguồn.\n"
        "QUY TẮC TÍNH TOÁN (ZERO-HALLUCINATION MATH):\n"
        "- Nếu câu hỏi có chứa số liệu cần tính toán, quy đổi tài chính, BẮT BUỘC viết mã Python trong khối ```python ... ```.\n"
        "- Đặt tên biến không dấu, viết thường, nối bằng gạch dưới (VD: `gia_vang`, `chiet_khau`).\n"
        "- Lưu kết quả vào biến `result` hoặc `ket_qua` và dùng `print()` in ra."
    )
    
    prompt = f"""
[LỊCH SỬ HỘI THOẠI GẦN ĐÂY]:
{history_context_str if history_context_str else "Không có lịch sử trước đó."}

[NGỮ CẢNH TÀI LIỆU NỘI BỘ]:
{combined_context}

[CÂU HỎI HIỆN TẠI]: {question}
"""
    
    llm_res = query_local_llm(prompt, system_prompt)
    if not llm_res["success"]:
        return {"success": False, "error": llm_res["error"]}
        
    ai_response_text = llm_res["response"]
    
    sandbox_execution_result = None
    python_code_blocks = re.findall(r"```python\s*(.*?)\s*```", ai_response_text, re.DOTALL)
    
    if python_code_blocks:
        target_code = python_code_blocks[0].strip()
        sandbox_execution_result = run_secure_sandbox(code_str=target_code, timeout_seconds=3)
        
        if sandbox_execution_result and sandbox_execution_result.get("success"):
            raw_output = sandbox_execution_result.get("output", "")
            vietnamese_summary = format_sandbox_result_to_vietnamese(question, target_code, raw_output)
            sandbox_execution_result["formatted_vietnamese_summary"] = vietnamese_summary
            ai_response_text += f"\n\n**Kết quả tính toán chuẩn xác:**\n{vietnamese_summary}"

    if chat_session:
        ChatMessage.objects.create(
            session=chat_session, 
            sender="ai", 
            text=ai_response_text,
            metadata={"citations": citations, "sandbox": sandbox_execution_result}
        )

    return {
        "success": True,
        "refusal": False,
        "session_id": str(chat_session.session_id) if chat_session else None,
        "answer": ai_response_text,
        "citations": citations,
        "sandbox_execution": sandbox_execution_result
    }