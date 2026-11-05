from django.shortcuts import render

# Định nghĩa thêm alias dashboard_home để tránh lỗi ImportError
def dashboard_home(request):
    return render(request, 'dashboard/base_layout.html')