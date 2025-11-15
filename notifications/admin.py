# notifications/admin.py (수정)

from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # ❗️ [수정] 'content'를 'message'로 변경
    list_display = ('user', 'message', 'notification_type', 'is_read', 'created_at')
    # 필터링 옵션 추가
    list_filter = ('is_read', 'notification_type')
    # ❗️ [수정] 'content'를 'message'로 변경
    search_fields = ('user__username', 'message') # 👈 여기도 수정