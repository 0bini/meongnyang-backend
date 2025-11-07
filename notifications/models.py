# notifications/models.py

from django.db import models
from django.conf import settings # ❗️ settings.AUTH_USER_MODEL을 사용하기 위해 import

# ❗️ 알림을 클릭했을 때 이동할 링크의 종류
# (예: 'comment' -> '/community/posts/10/')
NOTIFICATION_TYPES = [
    ('message', '새 쪽지'),
    ('comment', '새 댓글'),
    ('like', '게시글 좋아요'),
    # (추후 알림 종류 추가 가능)
]

class Notification(models.Model):
    """
    API 명세서 10.x: 알림 모델
    """
    # 1. 알림을 받는 사용자 (User 모델을 ForeignKey로 참조)
    #    'settings.AUTH_USER_MODEL'은 'users.User'를 안전하게 참조하는 방식입니다.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name="알림 수신자"
    )
    
    # 2. 알림 내용 (예: "댕댕집사님이 댓글을 남겼습니다.")
    content = models.CharField(max_length=255, verbose_name="알림 내용")
    
    # 3. 알림 읽음 여부
    is_read = models.BooleanField(default=False, verbose_name="읽음 여부")
    
    # 4. 알림 발생 시간 (자동 생성)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="발생 시간")
    
    # 5. 알림 종류 (필터링을 위해)
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES,
        verbose_name="알림 종류"
    )
    
    # 6. 클릭 시 이동할 링크 (API 10.1 Response의 'link' 필드)
    link = models.CharField(max_length=255, blank=True, null=True, verbose_name="관련 링크")

    class Meta:
        # 최신 알림이 맨 위에 오도록 정렬
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}님에게 온 알림: {self.content}"