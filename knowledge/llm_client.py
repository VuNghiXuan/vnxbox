# File path: knowledge/llm_client.py
# Chú thích: Tăng thời gian timeout cho Ollama để tránh bị ngắt quãng khi xử lý văn bản dài.

import requests
import logging

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL_NAME = "qwen2.5-coder" # Hoặc tên model Sếp đang cấu hình

# File path: knowledge/llm_client.py
# Chỉnh sửa chữ ký hàm để nhận thêm system_prompt hoặc các kwargs khác

def query_local_llm(prompt_text: str, task_type="text", timeout=600, system_prompt=None, **kwargs):
    """
    Hàm gọi Ollama local, hỗ trợ nhận thêm system_prompt để tránh lỗi unexpected keyword argument.
    """
    # Nếu có system_prompt, gộp chung vào prompt gửi đi cho Ollama
    final_prompt = prompt_text
    if system_prompt:
        final_prompt = f"System Instruction: {system_prompt}\n\nUser Request: {prompt_text}"

    payload = {
        "model": LOCAL_MODEL_NAME,
        "prompt": final_prompt,
        "stream": False
    }
    
    try:
        logger.info(f"🚀 [Ollama Client] Đang gửi yêu cầu tới model {LOCAL_MODEL_NAME} (Timeout: {timeout}s)...")
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        result_data = response.json()
        return {
            "success": True,
            "response": result_data.get("response", "")
        }
    except requests.exceptions.Timeout:
        logger.error(f"❌ [Ollama Error] Quá thời gian chờ (Timeout {timeout}s) khi gọi LLM.")
        return {
            "success": False,
            "response": "⚠️ Hệ thống LLM cục bộ (Ollama) mất quá nhiều thời gian phản hồi. Vui lòng thử lại sau."
        }
    except Exception as e:
        logger.error(f"❌ [Ollama Error] Lỗi kết nối Ollama: {str(e)}")
        return {
            "success": False,
            "response": f"⚠️ Không thể kết nối tới Ollama tại localhost:11434. Chi tiết: {str(e)}"
        }