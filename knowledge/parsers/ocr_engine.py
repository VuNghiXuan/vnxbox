# File path: knowledge/parsers/ocr_engine.py
# Chú thích: Module quản lý EasyOCR Lazy Loading trên CPU (Chạy tối ưu cho máy không có GPU)

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