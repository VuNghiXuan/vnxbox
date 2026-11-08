# File path: knowledge/parsers/docling_parser.py
# Chú thích: Bổ sung bộ chuyển đổi tạm thời cho luồng truyền file Django vào Docling.

import tempfile
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def parse_with_docling(file_obj):
    """
    Hàm bóc tách tổng quát qua Docling, tự động xử lý file stream từ Django Upload.
    """
    try:
        from docling.document_converter import DocumentConverter
        
        # Nếu đầu vào là file object từ Django (có thuộc tính read)
        if hasattr(file_obj, 'read'):
            # Tạo file tạm trên đĩa để Docling nhận diện đúng kiểu Path/String
            suffix = os.path.splitext(file_obj.name)[1] if hasattr(file_obj, 'name') else ".tmp"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                tmp.write(file_obj.read())
                tmp_path = tmp.name
            
            try:
                converter = DocumentConverter()
                result = converter.convert(Path(tmp_path))
                markdown_text = result.document.export_to_markdown()
                return {"success": True, "text": markdown_text}
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            # Trường hợp truyền đường dẫn trực tiếp
            converter = DocumentConverter()
            result = converter.convert(Path(file_obj))
            return {"success": True, "text": result.document.export_to_markdown()}

    except Exception as e:
        logger.debug(f"Docling chưa khả dụng hoặc lỗi cấu trúc: {str(e)}")
        return {"success": False, "error": str(e)}