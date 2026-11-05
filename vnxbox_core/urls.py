from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse


urlpatterns = [
    path('', include('dashboard.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('knowledge.urls')),
]