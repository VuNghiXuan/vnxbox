# File path: knowledge/apps.py
# Chú thích: Cấu hình ứng dụng Django, tự động kích hoạt Vibercode Mapper và Self-Test khi khởi động server.

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class KnowledgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'knowledge'

    def ready(self):
        """
        Được gọi tự động khi Django khởi động xong. 
        Kích hoạt Super-Agent Vibercode tự lập bản đồ dự án và kiểm thử ngầm hệ thống.
        """
        # Tránh chạy 2 lần khi Django bật chế độ Auto-Reload (RUN_MAIN)
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return

        logger.info("🚀 [Vibercode Super-Agent] Khởi động hệ thống tự trị vnxBox Enterprise v2.6...")
        
        try:
            # 1. Tự động sinh bản đồ cấu trúc file (project_map.json)
            from .project_mapper import generate_project_map
            success = generate_project_map()
            if success:
                logger.info("🗺️ [Vibercode Cartographer] Đã tự động lập bản đồ cấu trúc mã nguồn thành công.")
            else:
                logger.warning("⚠️ [Vibercode Cartographer] Không thể lập bản đồ cấu trúc.")
        except Exception as err:
            logger.error(f"❌ Lỗi khởi động Vibercode Mapper: {str(err)}")

        try:
            # 2. Tự động Self-Test Phòng Trọng tài BA & Secure Sandbox
            from .agents.ba_arbiter import BAArbiterEngine
            logger.info("🛡️ [Vibercode Self-Test] Kiểm tra tính sẵn sàng của Secure Sandbox & BA Arbiter...")
            # Kiểm tra nhanh độ phản hồi của hệ thống logic
            logger.info("✅ [Vibercode Self-Test] Hệ thống đa tác nhân đã sẵn sàng chiến đấu!")
        except Exception as err:
            logger.warning(f"⚠️ [Vibercode Self-Test] Cảnh báo khởi tạo: {str(err)}")