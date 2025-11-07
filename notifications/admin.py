# notifications/admin.py

from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # 관리자 페이지 목록에 보일 필드들
    list_display = ('user', 'content', 'notification_type', 'is_read', 'created_at')
    # 필터링 옵션 추가
    list_filter = ('is_read', 'notification_type')
    # 검색 기능 추가
    search_fields = ('user__username', 'content')