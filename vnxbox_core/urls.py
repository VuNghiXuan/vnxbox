# File path: vnxbox/urls.py (hoặc settings.ROOT_URLCONF)
# Chú thích: Tổng hợp Root URLs điều hướng toàn bộ hệ thống vnxBox Enterprise.

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('dashboard.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('knowledge.urls')),
]