# notifications/serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    """
    API 명세서 10.1: 알림 목록 조회를 위한 Serializer
    """

    class Meta:
        model = Notification
        # ❗️ [수정] fields 리스트에서 'content'를 'message'로 변경
        fields = [
            'id', 'message', 'is_read', 'created_at', 'link', 'notification_type'
        ]
        read_only_fields = fields