# File path: knowledge/project_mapper.py
# Chú thích: Script tự động quét cấu trúc mã nguồn Django, sinh project_map.json cho Super-Agent Vibercode.

import os
import json
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "project_map.json")

EXCLUDE_DIRS = {".git", "__pycache__", "venv", "env", "node_modules", "staticfiles", "media"}
EXCLUDE_EXTS = {".pyc", ".sqlite3", ".log", ".png", ".jpg", ".pdf"}


def generate_project_map():
    """
    Quét toàn bộ thư mục dự án, trích xuất cấu trúc thư mục, tên file và 
    các thành phần quan trọng để cung cấp bản đồ thu gọn cho AI Vibercode.
    """
    logger.info("🗺️ [Vibercode Mapper] Bắt đầu quét cấu trúc dự án vnxBox Enterprise...")
    
    structure = {
        "project_name": "vnxBox Enterprise v2.6",
        "root_directory": PROJECT_ROOT,
        "directories": {}
    }

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Lọc bỏ các thư mục rác
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        rel_path = os.path.relpath(root, PROJECT_ROOT)
        if rel_path == ".":
            rel_path = "root"

        file_list = []
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext not in EXCLUDE_EXTS:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                file_list.append({
                    "file_name": file,
                    "size_bytes": file_size
                })

        if file_list:
            structure["directories"][rel_path] = {
                "files": file_list
            }

    # Lưu ra file json cục bộ
    try:
        with open(MAP_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ [Vibercode Mapper] Đã lập bản đồ thành công tại: {MAP_OUTPUT_PATH}")
        return True
    except Exception as err:
        logger.error(f"❌ [Vibercode Mapper] Không thể ghi file bản đồ: {str(err)}")
        return False


if __name__ == "__main__":
    generate_project_map()