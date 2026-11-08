# File path: knowledge/management/commands/run_corporation.py
# Chú thích: Django Management Command - Vận hành trọn gói Tập đoàn AI vnxBox (DAG Tasks -> Viber Protocol -> Viber Test Generator).

from django.core.management.base import BaseCommand
from knowledge.agents.execution_dispatcher import ExecutionDispatcher
from knowledge.agents.viber_protocol_bridge import ViberProtocolBridge
from knowledge.agents.viber_test_generator import ViberTestGenerator


class Command(BaseCommand):
    help = 'Khởi động dây chuyền tự trị toàn diện của Tập đoàn AI vnxBox Enterprise'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 [Management Command] Đang nạp Bản chỉ dẫn kiến trúc vnxBox v2.6..."))

        blueprint_text = (
            "Hệ thống vnxBox Enterprise v2.6 - Blueprint-Driven Autonomous Corporation. "
            "Yêu cầu quản lý quy trình tự trị đa phòng ban, kiểm thử tự động, tích hợp Secure Sandbox và bảo mật local-first."
        )

        # 1. Chạy chuỗi phân rã và thực thi DAG Tasks qua Execution Dispatcher
        results = ExecutionDispatcher.run_corporation_pipeline(blueprint_text)

        # 2. Phát tín hiệu đồng bộ qua Viber Protocol Bridge
        if results:
            self.stdout.write(self.style.NOTICE("⚡ [Viber Protocol] Đang phát tín hiệu đồng bộ kết quả giữa các phòng ban..."))
            sync_success = ViberProtocolBridge.dispatch_viber_signal(results)
            if sync_success:
                self.stdout.write(self.style.SUCCESS("✅ [Viber Protocol Success] Hệ thống đa tác nhân đã đồng bộ toàn vẹn trạng thái!"))

            # 3. Kích hoạt QA Lead sinh Test Case chuyên sâu theo tiêu chuẩn vnxBox
            self.stdout.write(self.style.NOTICE("🧪 [QA Department] Đang tổng hợp và sinh bộ kịch bản Test Case chi tiết..."))
            test_report = ViberTestGenerator.generate_detailed_test_cases(
                feature_title="Hệ thống Vận hành Tự trị vnxBox Enterprise & Quản lý Kho Vàng",
                feature_specification="Xác thực toàn bộ các luồng tác vụ từ khởi tạo database, xử lý API backend, điều phối DAG, đến giao diện UI và kiểm định an toàn."
            )

            self.stdout.write("\n" + "="*50 + "\n📋 BỘ KỊCH BẢN KIỂM THỬ (QA TEST REPORT):\n" + "="*50)
            self.stdout.write(test_report)
            self.stdout.write("\n" + "="*50 + "\n")

        self.stdout.write(self.style.SUCCESS(f"🏆 Hoàn tất toàn bộ chuỗi Tập đoàn AI! Đã xử lý {len(results)} tác vụ và sinh hoàn tất tài liệu kiểm thử."))