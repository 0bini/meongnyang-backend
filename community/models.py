# community/models.py
from django.db import models
from users.models import User # users 앱의 User 모델 import

class Post(models.Model):
    """게시글 모델"""
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name="작성자")
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="내용")
    image = models.ImageField(upload_to='post_images/', blank=True, null=True, verbose_name="첨부 이미지") # Pillow 필요
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True, verbose_name="좋아요 누른 사람")

    class Meta:
        ordering = ['-created_at'] # 최신 글부터 정렬

    def __str__(self):
        return self.title

    @property
    def like_count(self):
        """좋아요 개수를 계산하는 속성"""
        return self.likes.count()

class Comment(models.Model):
    """댓글 모델"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="게시글")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name="작성자")
    content = models.TextField(verbose_name="댓글 내용")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at'] # 작성 순서대로 정렬

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"

class Message(models.Model):
    """쪽지 모델"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name="보낸 사람")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', verbose_name="받는 사람")
    content = models.TextField(verbose_name="쪽지 내용")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="보낸 시각")
    is_read = models.BooleanField(default=False, verbose_name="읽음 여부")

    class Meta:
        ordering = ['-sent_at'] # 최신 메시지부터 정렬

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"

# 알림(Notification) 모델은 필요 시 별도 앱 또는 기능으로 구현합니다.
# 예를 들어, Notification 모델을 만들고 Comment, Message 생성 시
# signal 등을 이용해 Notification 객체를 생성하는 방식으로 구현할 수 있습니다.

