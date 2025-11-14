# notifications/serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    """
    API 명세서 10.1: 알림 목록 조회를 위한 Serializer
    """
    
    # ❗️ 1. [추가] 보낸 사람의 닉네임을 가져올 필드
    # (Notification 모델에 sender 필드가 있다는 가정)
    sender_nickname = serializers.ReadOnlyField(source='sender.nickname')
    
    # ❗️ 2. [추가] 보낸 사람의 ID를 가져올 필드
    sender_id = serializers.ReadOnlyField(source='sender.id')

    class Meta:
        model = Notification
        # ❗️ 3. [수정] fields 리스트에 'sender_nickname', 'sender_id' 추가
        fields = [
            'id', 'content', 'is_read', 'created_at', 'link', 'notification_type', 
            'sender_nickname', 'sender_id' 
        ]
        read_only_fields = fields