# community/serializers.py
from rest_framework import serializers
from .models import Post, Comment, Message
from users.models import User # User 모델 import

class CommentSerializer(serializers.ModelSerializer):
    """
    API 명세서 8.4, 8.5: 댓글(Comment)을 위한 Serializer
    (댓글 작성, 조회, 수정, 삭제)
    """
    # 댓글을 보여줄 때, 작성자의 닉네임을 함께 보여주기 위해 추가
    author_nickname = serializers.ReadOnlyField(source='author.nickname')

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'author_nickname', 'content', 'created_at']
        # 'author'와 'post'는 읽기 전용으로 설정합니다. 
        # (View에서 자동으로 채워줄 것이기 때문)
        read_only_fields = ['id', 'author', 'author_nickname', 'post', 'created_at']

class PostSerializer(serializers.ModelSerializer):
    """
    API 명세서 8.1, 8.2, 8.3: 게시글(Post)을 위한 Serializer
    (게시글 목록, 작성, 상세 조회, 수정, 삭제)
    """
    # 게시글을 보여줄 때, 작성자의 닉네임을 함께 보여주기 위해 추가
    author_nickname = serializers.ReadOnlyField(source='author.nickname')
    # 이 게시글에 달린 댓글들을 함께 보여주기 위해 Nested Serializer 사용
    # (읽기 전용, 'many=True'로 여러 개를 가져옴)
    comments = CommentSerializer(many=True, read_only=True)
    
    # '좋아요' 개수를 보여주기 위해 추가
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_nickname', 'title', 'content', 'image', 
            'created_at', 'updated_at', 'likes_count', 'comments'
        ]
        # 'author'는 View에서 자동으로 설정할 것이므로 읽기 전용
        read_only_fields = ['id', 'author', 'author_nickname', 'created_at', 'updated_at', 'likes_count', 'comments']
    
    def get_likes_count(self, obj):
        # Post 모델에 정의된 likes(ManyToManyField)의 개수를 반환
        return obj.likes.count()
    
class MessageSerializer(serializers.ModelSerializer):
    """
    API 명세서 9.x: 쪽지(Message)를 위한 Serializer
    """
    sender_nickname = serializers.ReadOnlyField(source='sender.nickname')
    receiver_nickname = serializers.ReadOnlyField(source='receiver.nickname')

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_nickname', 'receiver', 'receiver_nickname', 
            'content', 'sent_at', 'is_read'  # ❗️ [오류 수정] 'timestamp' -> 'sent_at'
        ]
        read_only_fields = ['id', 'sender', 'sender_nickname', 'receiver_nickname', 'sent_at', 'is_read'] # ❗️ [오류 수정] 'timestamp' -> 'sent_at'