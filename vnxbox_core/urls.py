# File path: vnxbox/urls.py
# Chú thích: Tổng hợp Root URLs điều hướng toàn bộ hệ thống vnxBox Enterprise. Đã thiết lập viber_chat_interface làm trang chính (Homepage).

from django.contrib import admin
from django.urls import path, include
from knowledge.views import viber_chat_view  # 👈 Import trực tiếp view khung chat chính

urlpatterns = [
    # ⚡ Biến viber_chat_interface thành Giao diện chính (Trang chủ) tại đường dẫn gốc '/'
    path('', viber_chat_view, name='viber_homepage_main'),

    # Trang quản trị Django Admin
    path('admin/', admin.site.urls),
    
    # Gom toàn bộ API vào tiền tố /api/
    path('api/', include('knowledge.urls')),
    
    # Include toàn bộ đường dẫn từ ứng dụng knowledge (bao gồm /chat/, /war-room/, v.v.)
    path('', include('knowledge.urls')),
]