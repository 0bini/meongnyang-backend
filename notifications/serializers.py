# notifications/serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    """
    API 명세서 10.1: 알림 목록 조회를 위한 Serializer
    """
    
    # 참고: API 명세서에 'created_at'이 "5분 전" 같은 상대 시간으로 되어있습니다.
    # 하지만 여기서는 우선 기본 시간(ISO 형식)으로 보내고 
    # 프론트엔드에서 "X분 전"으로 변환하는 것을 더 권장합니다.
    # (SerializerMethodField를 사용해 서버에서 직접 만들 수도 있습니다.)

    class Meta:
        model = Notification
        # API 10.1 Response Body에 필요한 필드들
        fields = ['id', 'content', 'is_read', 'created_at', 'link', 'notification_type']
        # 모든 필드는 서버에서 제공하는 읽기 전용 데이터입니다.
        read_only_fields = fields