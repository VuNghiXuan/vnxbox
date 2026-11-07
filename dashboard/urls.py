# File path: dashboard/urls.py
# Chú thích: Định nghĩa URLs cho phân hệ Dashboard & Giao diện trang chủ vnxBox Enterprise.

from django.urls import path
from .views import dashboard_home

urlpatterns = [
    path('', dashboard_home, name='dashboard-home'),
]