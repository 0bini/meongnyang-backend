from django.db import models
from users.models import User # ❗️ users 앱의 User 모델을 임포트합니다.

class Notification(models.Model):
    """
    알림 모델
    """
    
    # 알림을 '받는' 유저 (알림의 주인)
    user = models.ForeignKey(
        User, 
        related_name='notifications', 
        on_delete=models.CASCADE, 
        verbose_name="알림 수신자"
    )
    
    # ❗️ [추가!] 알림을 '유발시킨' 유저 (예: 쪽지 보낸 사람)
    # (null=True, blank=True: 기존에 sender가 없던 알림 데이터와 호환시키기 위해 허용)
    sender = models.ForeignKey(
        User, 
        related_name='sent_notifications', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="알림 유발자"
    )
    
    # ❗️ [수정!] "message"가 아니라 "content"가 맞습니다.
    content = models.CharField(max_length=255, verbose_name="알림 내용")
    
    # 알림 타입 (예: 'MESSAGE', 'COMMENT', 'LIKE' 등)
    notification_type = models.CharField(max_length=50, verbose_name="알림 타입")
    
    # 읽음 여부
    is_read = models.BooleanField(default=False, verbose_name="읽음 여부")
    
    # 생성 날짜
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시각")
    
    # (선택) 알림 클릭 시 이동할 링크
    link = models.URLField(blank=True, null=True, verbose_name="관련 링크")

    class Meta:
        ordering = ['-created_at'] # 최신 알림부터 정렬

    def __str__(self):
        return f"[{self.user.username}] {self.content}" # 👈 content로 수정