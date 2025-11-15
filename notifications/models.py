# notifications/models.py (sender 필드가 삭제된 상태)
from django.db import models
from users.models import User # User 모델 임포트

class Notification(models.Model):
    """
    알림 모델
    """
    
    user = models.ForeignKey(
        User, 
        related_name='notifications', 
        on_delete=models.CASCADE, 
        verbose_name="알림을 받는 유저"
    )
    
    # ❗️ [삭제됨] sender = models.ForeignKey(...) 필드가 없습니다.
    
    message = models.CharField(max_length=255) # ❗️ 필드명은 'message' 그대로 둡니다. (이전 문제로 인해)
    notification_type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at'] 

    def __str__(self):
        return f"[{self.user.username}] {self.message}"