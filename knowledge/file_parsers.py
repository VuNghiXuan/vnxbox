import io
import csv
import json
from pypdf import PdfReader
from PIL import Image

# Global EasyOCR Reader (chạy CPU an toàn)
_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False, verbose=False)
    return _ocr_reader


def call_local_llm_for_taxonomy_and_faqs(raw_text, file_name, sheet_name=None):
    """
    Gọi LLM Local (Ollama - qwen2.5) để tự động phân loại Taxonomy
    (domain_name, sub_domain) và sinh tập câu hỏi định tuyến (Intent FAQs).
    """
    import urllib.request
    
    context_info = f"File: {file_name}" + (f" | Sheet: {sheet_name}" if sheet_name else "")
    prompt = f"""
Bạn là chuyên gia phân loại dữ liệu doanh nghiệp B2B (Auto-Taxonomy Engine).
Dựa vào nội dung tài liệu dưới đây, hãy phân tích và trả về định dạng JSON thuần túy (không chứa markdown codeblock):

1. domain_name: Lĩnh vực nghiệp vụ lớn (VD: "Nghiệp vụ Vàng bạc", "Kế toán - Tài chính", "Sản xuất - Định mức").
2. sub_domain: Nghiệp vụ chi tiết (VD: "Thu đổi vàng", "Tính giá vốn", "Bảo trì thiết bị").
3. title: Tiêu đề đại diện ngắn gọn cho phân đoạn này.
4. summary: Tóm tắt 1-2 câu về nội dung chính.
5. intent_faqs: Danh sách 5 - 10 câu hỏi thực tế mà người dùng/nhân viên có thể hỏi liên quan đến dữ liệu này.

Thông tin nguồn: {context_info}
Nội dung tài liệu:
{raw_text[:3000]}

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
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps({
                "model": "qwen2.5",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            parsed_json = json.loads(res_data.get("response", "{}"))
            return parsed_json
    except Exception as e:
        # Fallback an toàn nếu LLM chưa sẵn sàng
        return {
            "domain_name": "Nghiệp vụ Tổng hợp",
            "sub_domain": sheet_name if sheet_name else "Tri thức chung",
            "title": f"Tài liệu từ {file_name}",
            "summary": "Tài liệu được tải lên tự động",
            "intent_faqs": [f"Nội dung trong file {file_name} quy định gì?"]
        }


def format_context_header(domain_name, sub_domain, file_name, sheet_name, location_code, content):
    """
    Bơm khối Context Header chuẩn mực vào đầu mỗi đoạn tri thức.
    """
    header = f"""==================================================
CONTEXT HEADER:
- DOMAIN: {domain_name}
- SUB_DOMAIN: {sub_domain}
- SOURCE_FILE: {file_name}"""
    if sheet_name:
        header += f" | SHEET: {sheet_name}"
    header += f"\n- LOCATION: {location_code}\n==================================================\n"
    return header + content


def parse_uploaded_file(file_obj):
    """
    Module trích xuất & Phân loại Cấu trúc Tri thức Nâng cao (Structured Ingestion)
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
        # 3. XỬ LÝ FILE WORD (.docx) & MARKDOWN/TEXT
        # ==========================================
        elif file_name_lower.endswith('.docx'):
            from docx import Document
            doc = Document(file_obj)
            blocks = []

            for para in doc.paragraphs:
                if para.text.strip():
                    blocks.append(para.text.strip())

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
                        except Exception:
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
        return {"success": False, "error": f"Lỗi bóc tách file ({file_name}): {str(e)}"}