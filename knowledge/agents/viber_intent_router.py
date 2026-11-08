# File path: knowledge/agents/viber_intent_router.py
# Chú thích: Dynamic Semantic Intent Router - Phân loại ý định hoàn toàn bằng AI, không hardcode từ khóa.

import logging
import json
from typing import Dict, Any
from ..llm_client import query_local_llm

logger = logging.getLogger(__name__)


class ViberIntentRouter:
    """
    Trạm định tuyến ý định động (Dynamic Semantic Intent Router):
    Sử dụng model AI local để hiểu ngữ nghĩa câu lệnh của người dùng,
    tự động phân định xem cần phản hồi nhanh (CHAT_FAST) hay kích hoạt chuỗi tác vụ tập đoàn (CORPORATE_ACTION).
    """

    @classmethod
    def classify_intent(cls, user_message: str) -> Dict[str, Any]:
        """
        Phân tích ý định ngữ nghĩa từ câu chat của Sếp mà không dùng hardcode từ khóa.
        """
        logger.info(f"🔍 [Dynamic Intent Router] Đang phân tích ngữ nghĩa câu lệnh: '{user_message}'")

        prompt = f"""
        Bạn là Trưởng phòng Điều phối Ý định (Intent Router) của vnxBox Enterprise.
        Nhiệm vụ của bạn là phân tích câu lệnh sau của người dùng và quyết định xem đây là:
        1. "CHAT_FAST": Yêu cầu tra cứu thông tin nhanh, hỏi đáp thông thường, giải đáp thắc mắc, viết code ngắn hoặc trò chuyện.
        2. "CORPORATE_ACTION": Yêu cầu vận hành hệ thống, tính toán nghiệp vụ phức tạp đa bước, bóc tách tài liệu, sinh test case, hoặc chạy quy trình tự trị đa phòng ban.

        Câu lệnh người dùng: "{user_message}"

        Trả về kết quả DUY NHẤT dưới dạng định dạng JSON chuẩn (không kèm giải thích rườm rà), cấu trúc như sau:
        {{"intent_type": "CHAT_FAST hoặc CORPORATE_ACTION", "confidence": 0.95, "reason": "lý do ngắn gọn"}}
        """

        try:
            # Gọi LLM local với timeout ngắn (5-10 giây) để Router phản hồi cực nhanh
            res = query_local_llm(prompt, task_type="text", timeout=15)
            response_text = res.get("response", "").strip()

            # Trích xuất JSON từ kết quả phản hồi của LLM
            if "{" in response_text and "}" in response_text:
                json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
                parsed = json.loads(json_str)
                intent_type = parsed.get("intent_type", "CHAT_FAST")
                if intent_type not in ["CHAT_FAST", "CORPORATE_ACTION"]:
                    intent_type = "CHAT_FAST"
                
                logger.info(f"⚡ [Dynamic Intent Router] AI đã định tuyến thành công: {intent_type}")
                return {
                    "intent_type": intent_type,
                    "confidence": parsed.get("confidence", 0.90),
                    "description": parsed.get("reason", "Phân loại động bởi AI Model.")
                }
        except Exception as e:
            logger.warning(f"⚠️ [Intent Router Fallback] Lỗi phân tích ngữ nghĩa AI ({str(e)}), chuyển về chế độ mặc định.")

        # Fallback an toàn nếu LLM bận
        return {
            "intent_type": "CHAT_FAST",
            "confidence": 0.80,
            "description": "Fallback mặc định về phản hồi nhanh."
        }