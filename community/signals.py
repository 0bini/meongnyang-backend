# community/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

# 1. 알림을 받을/보낼 User 모델 (users/models.py)
from users.models import User 

# 2. 이벤트가 발생할 모델 (community/models.py)
from .models import Comment, Message, Post 

# 3. 생성할 알림 모델 (notifications/models.py)
from notifications.models import Notification

# --- 예시 1: 새 댓글이 달리면 게시글 작성자에게 알림 ---
@receiver(post_save, sender=Comment)
def notify_post_author_on_comment(sender, instance, created, **kwargs):
    """
    Comment 모델이 'post_save' (생성)될 때 실행됩니다.
    """
    if created:
        comment = instance
        post = comment.post
        post_author = post.author
        comment_author = comment.author

        # 1. 내 게시글에 내가 댓글 단 경우 (셀프 알림 방지)
        if post_author == comment_author:
            return

        # 2. 알림 내용 생성
        content = f"{comment_author.nickname}님이 회원님의 게시글에 댓글을 남겼습니다."
        
        # 3. 알림 클릭 시 이동할 링크
        # ❗️ [수정] config/urls.py와 community/urls.py를 반영한 주소
        link_to = f"/api/v1/community/posts/{post.id}/"

        # 4. 알림 객체 생성
        Notification.objects.create(
            user=post_author,             # 알림을 받을 사람: 게시글 작성자
            content=content,              # 알림 내용
            notification_type='comment',  # 알림 종류
            link=link_to                  # 클릭 시 이동할 URL
        )

# --- 예시 2: 새 쪽지가 오면 수신자에게 알림 ---
@receiver(post_save, sender=Message)
def notify_receiver_on_message(sender, instance, created, **kwargs):
    """
    Message 모델이 'post_save' (생성)될 때 실행됩니다.
    """
    if created:
        message = instance
        sender_user = message.sender
        receiver_user = message.receiver

        # 1. (혹시 모를) 자기 자신에게 쪽지를 보낸 경우 (셀프 알림 방지)
        if sender_user == receiver_user:
            return

        # 2. 알림 내용 생성
        content = f"{sender_user.nickname}님으로부터 새 쪽지가 도착했습니다."
        
        # 3. 알림 클릭 시 이동할 링크 (쪽지함)
        # ❗️ [수정] config/urls.py를 반영한 주소
        link_to = f"/api/v1/messages/"

        # 4. 알림 객체 생성
        Notification.objects.create(
            user=receiver_user,           # 알림을 받을 사람: 쪽지 수신자
            content=content,              # 알림 내용
            notification_type='message',  # 알림 종류
            link=link_to                  # 클릭 시 이동할 URL
        )