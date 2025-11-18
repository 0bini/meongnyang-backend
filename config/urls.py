"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# config/urls.py
# (기존 파일 수정)

from django.contrib import admin
from django.urls import path, include  # ⬅️ include는 이미 import 되어 있을 겁니다.
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. 앱별 URL 연결
    path('api/v1/users/', include('users.urls')),
    path('api/v1/pets/', include('pets.urls')),       
    
    # ⬇️ [수정] API 8.x (커뮤니티)
    path('api/v1/community/', include('community.urls')), 
    
    # ⬇️ [수정] API 9.x (쪽지) -> community 앱의 message_urls.py를 사용
    path('api/v1/messages/', include('community.message_urls')),
    
    # ⬇️ [진행 중] 10.x 알림 API
    path('api/v1/notifications/', include('notifications.urls')), 
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)