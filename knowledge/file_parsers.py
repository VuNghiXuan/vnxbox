# File path: knowledge/file_parsers.py
# Chú thích: Module trích xuất & Phân loại Cấu trúc Tri thức Nâng cao (Structured Ingestion)
# Hỗ trợ: Excel (Sheet-Aware), CSV, DOCX, PDF (Text & OCR), Images (EasyOCR), Text/MD.
# Đã tích hợp Hardware Auto-Profiling từ ai_services để tự động điều chỉnh tải xử lý.

import io
import csv
import json
import logging
from pypdf import PdfReader
from PIL import Image

from .ai_services import query_local_llm

logger = logging.getLogger(__name__)

# Global EasyOCR Reader (chạy CPU an toàn)
_ocr_reader = None

def get_ocr_reader():
    """
    Khởi tạo Lazy Loading cho EasyOCR Reader trên CPU để tránh chiếm dụng bộ nhớ khi chưa cần dùng.
    """
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False, verbose=False)
    return _ocr_reader


def call_local_llm_for_taxonomy_and_faqs(raw_text: str, file_name: str, sheet_name: str = None) -> dict:
    """
    Gọi LLM Local (thông qua ai_services) để tự động phân loại Taxonomy
    (domain_name, sub_domain) và sinh tập câu hỏi định tuyến (Intent FAQs).
    Tận dụng Hardware Auto-Profiling chống timeout.
    """
    context_info = f"File: {file_name}" + (f" | Sheet: {sheet_name}" if sheet_name else "")
    
    system_instruction = (
        "Bạn là chuyên gia phân loại dữ liệu doanh nghiệp B2B (Auto-Taxonomy Engine). "
        "Trả về kết quả JSON thuần túy, KHÔNG có markdown ```json bên ngoài."
    )
    
    prompt = f"""
Dựa vào nội dung tài liệu dưới đây, hãy phân tích và trả về định dạng JSON thuần túy:

1. domain_name: Lĩnh vực nghiệp vụ lớn (VD: "Nghiệp vụ Vàng bạc", "Kế toán - Tài chính", "Sản xuất - Định mức").
2. sub_domain: Nghiệp vụ chi tiết (VD: "Thu đổi vàng", "Tính giá vốn", "Bảo trì thiết bị").
3. title: Tiêu đề đại diện ngắn gọn cho phân đoạn này.
4. summary: Tóm tắt 1-2 câu về nội dung chính.
5. intent_faqs: Danh sách 5 - 10 câu hỏi thực tế mà người dùng/nhân viên có thể hỏi liên quan đến dữ liệu này.

Thông tin nguồn: {context_info}
Nội dung tài liệu:
---
{raw_text[:3000]}
---

CẤU TRÚC JSON BẮT BUỘC TRẢ VỀ:
{{
  "domain_name": "...",
  "sub_domain": "...",
  "title": "...",
  "summary": "...",
  "intent_faqs": ["câu hỏi 1?", "câu hỏi 2?", ...]
}}
"""
    try:
        res = query_local_llm(prompt, system_prompt=system_instruction, task_type="general")
        if res.get("success"):
            cleaned_text = res.get("response", "").replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_text)
    except Exception as e:
        logger.warning(f"Lỗi khi gọi Local LLM Auto-Taxonomy ({file_name}): {str(e)}")

    # Fallback dự phòng an toàn nếu LLM gặp sự cố
    return {
        "domain_name": "Nghiệp vụ Tổng hợp",
        "sub_domain": sheet_name if sheet_name else "Tri thức chung",
        "title": f"Tài liệu từ {file_name}",
        "summary": "Tài liệu được tải lên tự động",
        "intent_faqs": [f"Nội dung trong file {file_name} quy định gì?"]
    }


def format_context_header(domain_name: str, sub_domain: str, file_name: str, sheet_name: str, location_code: str, content: str) -> str:
    """
    Bơm khối Context Header chuẩn mực vào đầu mỗi đoạn tri thức chống mất ngữ cảnh khi Vectorize.
    """
    header = (
        "==================================================\n"
        "CONTEXT HEADER:\n"
        f"- DOMAIN: {domain_name}\n"
        f"- SUB_DOMAIN: {sub_domain if sub_domain else 'Chung'}\n"
        f"- SOURCE_FILE: {file_name}"
    )
    if sheet_name:
        header += f" | SHEET: {sheet_name}"
    header += f"\n- LOCATION: {location_code}\n==================================================\n\n"
    return header + content


def parse_uploaded_file(file_obj) -> dict:
    """
    Module trích xuất & Phân loại Cấu trúc Tri thức Nâng cao (Structured Ingestion).
    Trả về danh sách các Chapters đã sẵn sàng để lưu vào KnowledgeChapter & KnowledgeFAQ.
    """
    file_name = file_obj.name
    file_name_lower = file_name.lower()
    parsed_chapters = []

    try:
        # ==========================================
        # 1. XỬ LÝ FILE EXCEL (.xlsx) - SHEET-AWARE PARSING
        # ==========================================
        if file_name_lower.endswith('.xlsx'):
            import openpyxl
            wb = openpyxl.load_workbook(file_obj, data_only=True)

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    continue

                # Chuyển đổi bảng 2D thành Markdown Table chuẩn
                formatted_rows = []
                for row in rows:
                    cleaned_row = [str(cell).strip().replace('\n', ' ') if cell is not None else "" for cell in row]
                    if any(cleaned_row):
                        formatted_rows.append("| " + " | ".join(cleaned_row) + " |")

                if formatted_rows:
                    markdown_table = "\n".join(formatted_rows)
                    
                    # Gọi AI Phân loại & Sinh FAQs cho riêng Sheet này
                    ai_meta = call_local_llm_for_taxonomy_and_faqs(markdown_table, file_name, sheet_name)
                    
                    # Bơm Context Header
                    full_content = format_context_header(
                        domain_name=ai_meta.get("domain_name"),
                        sub_domain=ai_meta.get("sub_domain"),
                        file_name=file_name,
                        sheet_name=sheet_name,
                        location_code=f"Sheet: {sheet_name}",
                        content=markdown_table
                    )

                    parsed_chapters.append({
                        "source_file": file_name,
                        "sheet_name": sheet_name,
                        "domain_name": ai_meta.get("domain_name"),
                        "sub_domain": ai_meta.get("sub_domain"),
                        "chapter_code": f"Sheet: {sheet_name}",
                        "article_code": "Toàn bộ bảng",
                        "title": ai_meta.get("title", f"Phân hệ {sheet_name}"),
                        "summary": ai_meta.get("summary", ""),
                        "content": full_content,
                        "intent_faqs": ai_meta.get("intent_faqs", [])
                    })

        # ==========================================
        # 2. XỬ LÝ FILE CSV (.csv)
        # ==========================================
        elif file_name_lower.endswith('.csv'):
            content = file_obj.read()
            try:
                decoded_content = content.decode('utf-8')
            except UnicodeDecodeError:
                decoded_content = content.decode('latin-1', errors='ignore')

            csv_reader = csv.reader(io.StringIO(decoded_content))
            rows = ["| " + " | ".join([cell.strip() for cell in row]) + " |" for row in csv_reader if any(row)]
            markdown_table = "\n".join(rows)

            ai_meta = call_local_llm_for_taxonomy_and_faqs(markdown_table, file_name)
            full_content = format_context_header(
                domain_name=ai_meta.get("domain_name"),
                sub_domain=ai_meta.get("sub_domain"),
                file_name=file_name,
                sheet_name=None,
                location_code="CSV Data Table",
                content=markdown_table
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Bảng CSV",
                "article_code": "Dữ liệu dòng",
                "title": ai_meta.get("title", f"Dữ liệu từ {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": full_content,
                "intent_faqs": ai_meta.get("intent_faqs", [])
            })

        # ==========================================
        # 3. XỬ LÝ FILE WORD (.docx)
        # ==========================================
        elif file_name_lower.endswith('.docx'):
            from docx import Document
            doc = Document(file_obj)
            blocks = [para.text.strip() for para in doc.paragraphs if para.text.strip()]

            raw_text = "\n\n".join(blocks)
            ai_meta = call_local_llm_for_taxonomy_and_faqs(raw_text, file_name)
            full_content = format_context_header(
                domain_name=ai_meta.get("domain_name"),
                sub_domain=ai_meta.get("sub_domain"),
                file_name=file_name,
                sheet_name=None,
                location_code="Văn bản Word",
                content=raw_text
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Tài liệu Word",
                "article_code": "Nội dung chính",
                "title": ai_meta.get("title", f"Tài liệu {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": full_content,
                "intent_faqs": ai_meta.get("intent_faqs", [])
            })

        # ==========================================
        # 4. XỬ LÝ FILE PDF (.pdf - Text & OCR Scan)
        # ==========================================
        elif file_name_lower.endswith('.pdf'):
            reader = PdfReader(file_obj)
            page_blocks = []

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    page_blocks.append(f"[Trang {i+1}]\n" + page_text.strip())
                elif page.images:
                    reader_ocr = get_ocr_reader()
                    ocr_texts = []
                    for img_obj in page.images:
                        try:
                            image = Image.open(io.BytesIO(img_obj.data))
                            res = reader_ocr.readtext(image, detail=0)
                            if res:
                                ocr_texts.append(" ".join(res))
                        except Exception as ocr_err:
                            logger.debug(f"Lỗi OCR ảnh trong PDF trang {i+1}: {str(ocr_err)}")
                            continue
                    if ocr_texts:
                        page_blocks.append(f"[Trang {i+1} (OCR Scan)]\n" + "\n".join(ocr_texts))

            raw_text = "\n\n".join(page_blocks)
            if not raw_text.strip():
                return {"success": False, "error": "File PDF không thể trích xuất nội dung."}

            ai_meta = call_local_llm_for_taxonomy_and_faqs(raw_text, file_name)
            full_content = format_context_header(
                domain_name=ai_meta.get("domain_name"),
                sub_domain=ai_meta.get("sub_domain"),
                file_name=file_name,
                sheet_name=None,
                location_code="File PDF",
                content=raw_text
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Tài liệu PDF",
                "article_code": "Toàn văn",
                "title": ai_meta.get("title", f"Tài liệu {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": full_content,
                "intent_faqs": ai_meta.get("intent_faqs", [])
            })

        # ==========================================
        # 5. XỬ LÝ FILE ẢNH (.png, .jpg, .jpeg, .webp)
        # ==========================================
        elif file_name_lower.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            image = Image.open(file_obj)
            reader_ocr = get_ocr_reader()
            results = reader_ocr.readtext(image, detail=0)

            if not results:
                return {"success": False, "error": "Không tìm thấy văn bản nào trong ảnh."}

            raw_text = "\n".join(results)
            ai_meta = call_local_llm_for_taxonomy_and_faqs(raw_text, file_name)
            full_content = format_context_header(
                domain_name=ai_meta.get("domain_name"),
                sub_domain=ai_meta.get("sub_domain"),
                file_name=file_name,
                sheet_name=None,
                location_code="Hình ảnh OCR",
                content=raw_text
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "File Ảnh",
                "article_code": "Nội dung OCR",
                "title": ai_meta.get("title", f"Hình ảnh {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": full_content,
                "intent_faqs": ai_meta.get("intent_faqs", [])
            })

        # ==========================================
        # 6. XỬ LÝ FILE TEXT / MARKDOWN (.txt, .md)
        # ==========================================
        elif file_name_lower.endswith(('.txt', '.md')):
            content = file_obj.read()
            try:
                raw_text = content.decode('utf-8')
            except UnicodeDecodeError:
                raw_text = content.decode('latin-1', errors='ignore')

            ai_meta = call_local_llm_for_taxonomy_and_faqs(raw_text, file_name)
            full_content = format_context_header(
                domain_name=ai_meta.get("domain_name"),
                sub_domain=ai_meta.get("sub_domain"),
                file_name=file_name,
                sheet_name=None,
                location_code="Văn bản Thô",
                content=raw_text
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Văn bản Thô",
                "article_code": "Nội dung",
                "title": ai_meta.get("title", f"File văn bản {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": full_content,
                "intent_faqs": ai_meta.get("intent_faqs", [])
            })

        else:
            return {"success": False, "error": "Định dạng file không được hỗ trợ."}

        return {"success": True, "chapters": parsed_chapters}

    except Exception as e:
        logger.error(f"Lỗi bóc tách file ({file_name}): {str(e)}", exc_info=True)
        return {"success": False, "error": f"Lỗi bóc tách file ({file_name}): {str(e)}"}