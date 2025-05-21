from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('chatapp.urls')),            # 기존 채팅앱
    path('accounts/', include('accounts.urls')),  # ✅ 회원 기능 연결
]
