# File path: knowledge/file_parsers.py
# Chú thích: Module Router tiếp nhận & điều phối trích xuất file tài liệu (Ingestion Router).
# Tích hợp cơ chế ưu tiên Docling Layout Engine với Fallback an toàn tuyệt đối về PyPDF/python-docx.
# Tự động liên kết với TaxonomyEngine để bóc tách Công ty/Lĩnh vực và tự sinh nhân viên AI chuyên trách.

import io
import csv
import logging
from pypdf import PdfReader
from PIL import Image

from .parsers.ocr_engine import get_ocr_reader
from .parsers.taxonomy_engine import TaxonomyEngine
from .parsers.docling_parser import parse_with_docling

logger = logging.getLogger(__name__)


def parse_uploaded_file(file_obj, default_company_code: str = "GENERAL", default_domain: str = "Quy định chung") -> dict:
    """
    Module trích xuất & Phân loại Cấu trúc Tri thức Nâng cao (Structured Ingestion Router).
    Trả về danh sách các Chapters đã sẵn sàng để lưu vào KnowledgeChapter & KnowledgeFAQ,
    kèm thông tin Nhân viên AI chuyên trách vừa được tự sinh.
    """
    file_name = file_obj.name
    file_name_lower = file_name.lower()
    parsed_chapters = []

    try:
        # ==========================================
        # 1. XỬ LÝ FILE EXCEL (.xlsx) - SHEET-AWARE
        # ==========================================
        if file_name_lower.endswith('.xlsx'):
            import openpyxl
            wb = openpyxl.load_workbook(file_obj, data_only=True)

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    continue

                formatted_rows = []
                for row in rows:
                    cleaned_row = [str(cell).strip().replace('\n', ' ') if cell is not None else "" for cell in row]
                    if any(cleaned_row):
                        formatted_rows.append("| " + " | ".join(cleaned_row) + " |")

                if formatted_rows:
                    markdown_table = "\n".join(formatted_rows)
                    ai_meta = TaxonomyEngine.analyze_and_classify_chunk(
                        raw_chunk_text=markdown_table,
                        default_company_code=default_company_code,
                        default_domain=default_domain
                    )

                    parsed_chapters.append({
                        "source_file": file_name,
                        "sheet_name": sheet_name,
                        "company_code": ai_meta.get("company_code", default_company_code),
                        "domain_name": ai_meta.get("domain_name"),
                        "sub_domain": ai_meta.get("sub_domain"),
                        "chapter_code": f"Sheet: {sheet_name}",
                        "article_code": "Toàn bộ bảng",
                        "title": ai_meta.get("title", f"Phân hệ {sheet_name}"),
                        "summary": ai_meta.get("summary", ""),
                        "content": markdown_table,
                        "intent_faqs": ai_meta.get("faq_variations", []),
                        "assigned_agent": ai_meta.get("assigned_agent_name")
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

            ai_meta = TaxonomyEngine.analyze_and_classify_chunk(
                raw_chunk_text=markdown_table,
                default_company_code=default_company_code,
                default_domain=default_domain
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "company_code": ai_meta.get("company_code", default_company_code),
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Bảng CSV",
                "article_code": "Dữ liệu dòng",
                "title": ai_meta.get("title", f"Dữ liệu từ {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": markdown_table,
                "intent_faqs": ai_meta.get("faq_variations", []),
                "assigned_agent": ai_meta.get("assigned_agent_name")
            })

        # ==========================================
        # 3. XỬ LÝ FILE WORD (.docx) - DOCLING + FALLBACK PYTHON-DOCX
        # ==========================================
        elif file_name_lower.endswith('.docx'):
            docling_res = parse_with_docling(file_obj)
            raw_text = ""
            
            if docling_res and isinstance(docling_res, dict) and docling_res.get("success"):
                raw_text = docling_res.get("text", "")
            else:
                logger.info(f"Docling chưa sẵn sàng cho {file_name}, chuyển sang python-docx fallback an toàn.")
                from docx import Document
                # Đảm bảo con trỏ file stream được đưa về đầu nếu đã đọc trước đó
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                doc = Document(file_obj)
                
                blocks = []
                # Đọc các đoạn văn bản (Paragraphs)
                for para in doc.paragraphs:
                    if para.text.strip():
                        blocks.append(para.text.strip())
                
                # Đọc các bảng biểu (Tables) và chuyển hóa sang định dạng Markdown chuẩn
                for table in doc.tables:
                    table_rows = []
                    for row in table.rows:
                        row_cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
                        table_rows.append("| " + " | ".join(row_cells) + " |")
                    if table_rows:
                        blocks.append("\n" + "\n".join(table_rows) + "\n")

                raw_text = "\n\n".join(blocks)

            if not raw_text.strip():
                return {"success": False, "error": "File Word (.docx) trống hoặc không thể trích xuất nội dung."}

            ai_meta = TaxonomyEngine.analyze_and_classify_chunk(
                raw_chunk_text=raw_text,
                default_company_code=default_company_code,
                default_domain=default_domain
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "company_code": ai_meta.get("company_code", default_company_code),
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Tài liệu Word",
                "article_code": "Nội dung chính",
                "title": ai_meta.get("title", f"Tài liệu {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": raw_text,
                "intent_faqs": ai_meta.get("faq_variations", []),
                "assigned_agent": ai_meta.get("assigned_agent_name")
            })

        # ==========================================
        # 4. XỬ LÝ FILE PDF (.pdf) - DOCLING + FALLBACK
        # ==========================================
        elif file_name_lower.endswith('.pdf'):
            docling_res = parse_with_docling(file_obj)
            
            if docling_res and isinstance(docling_res, dict) and docling_res.get("success"):
                raw_text = docling_res.get("text", "")
            else:
                logger.info(f"Docling chưa sẵn sàng cho {file_name}, chuyển sang PyPDF/OCR fallback.")
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
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
                                logger.debug(f"Lỗi OCR ảnh PDF trang {i+1}: {str(ocr_err)}")
                                continue
                        if ocr_texts:
                            page_blocks.append(f"[Trang {i+1} (OCR Scan)]\n" + "\n".join(ocr_texts))

                raw_text = "\n\n".join(page_blocks)

            if not raw_text.strip():
                return {"success": False, "error": "File PDF không thể trích xuất nội dung."}

            ai_meta = TaxonomyEngine.analyze_and_classify_chunk(
                raw_chunk_text=raw_text,
                default_company_code=default_company_code,
                default_domain=default_domain
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "company_code": ai_meta.get("company_code", default_company_code),
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Tài liệu PDF",
                "article_code": "Toàn văn",
                "title": ai_meta.get("title", f"Tài liệu {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": raw_text,
                "intent_faqs": ai_meta.get("faq_variations", []),
                "assigned_agent": ai_meta.get("assigned_agent_name")
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
            ai_meta = TaxonomyEngine.analyze_and_classify_chunk(
                raw_chunk_text=raw_text,
                default_company_code=default_company_code,
                default_domain=default_domain
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "company_code": ai_meta.get("company_code", default_company_code),
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "File Ảnh",
                "article_code": "Nội dung OCR",
                "title": ai_meta.get("title", f"Hình ảnh {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": raw_text,
                "intent_faqs": ai_meta.get("faq_variations", []),
                "assigned_agent": ai_meta.get("assigned_agent_name")
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

            ai_meta = TaxonomyEngine.analyze_and_classify_chunk(
                raw_chunk_text=raw_text,
                default_company_code=default_company_code,
                default_domain=default_domain
            )

            parsed_chapters.append({
                "source_file": file_name,
                "sheet_name": None,
                "company_code": ai_meta.get("company_code", default_company_code),
                "domain_name": ai_meta.get("domain_name"),
                "sub_domain": ai_meta.get("sub_domain"),
                "chapter_code": "Văn bản Thô",
                "article_code": "Nội dung",
                "title": ai_meta.get("title", f"File văn bản {file_name}"),
                "summary": ai_meta.get("summary", ""),
                "content": raw_text,
                "intent_faqs": ai_meta.get("faq_variations", []),
                "assigned_agent": ai_meta.get("assigned_agent_name")
            })

        else:
            return {"success": False, "error": "Định dạng file không được hỗ trợ."}

        return {"success": True, "chapters": parsed_chapters}

    except Exception as e:
        logger.error(f"Lỗi bóc tách file ({file_name}): {str(e)}", exc_info=True)
        return {"success": False, "error": f"Lỗi bóc tách file ({file_name}): {str(e)}"}