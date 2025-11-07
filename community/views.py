from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model # ❗️ User 모델을 가져오기 위해
from django.db.models import Q # ❗️ OR 조건 검색을 위해

# ❗️ [수정] Message, MessageSerializer 추가
from .models import Post, Comment, Message
from .serializers import PostSerializer, CommentSerializer, MessageSerializer
# ❗️ [수정] UserSerializer import
from users.serializers import UserSerializer

User = get_user_model() # ❗️ User 모델 정의

# --- 권한 설정 ---
class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    객체의 작성자(author)만 수정/삭제할 수 있도록 하는 커스텀 권한입니다.
    읽기(GET)는 인증된 사용자라면 누구나 가능합니다.
    """
    def has_object_permission(self, request, view, obj):
        # 읽기 요청(GET, HEAD, OPTIONS)은 항상 허용합니다.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if isinstance(obj, (Post, Comment)):
            return obj.author == request.user
        if isinstance(obj, Message):
            return obj.sender == request.user
            
        return False

# --- 커뮤니티 API (API 8.x) ---

class PostViewSet(viewsets.ModelViewSet):
    """
    API 명세서 8.1, 8.2, 8.3: 게시글(Post) 관리(CRUD) ViewSet
    - GET /community/posts/
    - POST /community/posts/
    - GET /community/posts/{post_id}/
    - PUT /community/posts/{post_id}/
    - DELETE /community/posts/{post_id}/
    """
    queryset = Post.objects.all().order_by('-created_at') # 최신순으로 정렬
    serializer_class = PostSerializer
    
    # 권한 설정:
    # - IsAuthenticatedOrReadOnly: 로그인한 사용자는 모든 요청(읽기,쓰기) 가능, 비로그인 사용자는 읽기(GET)만 가능
    # - IsAuthorOrReadOnly: 수정(PUT)/삭제(DELETE)는 작성자 본인만 가능
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def perform_create(self, serializer):
        """
        POST 요청으로 새로운 게시글을 생성할 때,
        'author' 필드를 요청을 보낸 사용자로 자동 설정합니다.
        """
        serializer.save(author=self.request.user)

class CommentViewSet(viewsets.ModelViewSet):
    """
    API 명세서 8.4, 8.5: 댓글(Comment) 관리(CRUD) ViewSet
    - GET /community/posts/{post_id}/comments/
    - POST /community/posts/{post_id}/comments/
    - PUT /community/comments/{comment_id}/
    - DELETE /community/comments/{comment_id}/
    """
    queryset = Comment.objects.all().order_by('created_at') # 작성순으로 정렬
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        """
        GET 요청 시, 특정 게시글(post_id)에 달린 댓글 목록만 반환합니다.
        """
        # URL에서 post_id를 가져옵니다.
        post_id = self.kwargs.get('post_id')
        if post_id:
            return Comment.objects.filter(post_id=post_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        """
        POST 요청 시, 'author'는 현재 로그인한 사용자로,
        'post'는 URL에서 가져온 post_id로 자동 설정합니다.
        """
        post = get_object_or_404(Post, id=self.kwargs['post_id'])
        serializer.save(author=self.request.user, post=post)

class LikeView(APIView):
    """
    API 명세서 8.6: 좋아요(Like) 토글 View
    - POST /community/posts/{post_id}/like/
    """
    permission_classes = [permissions.IsAuthenticated] # 로그인한 사용자만 좋아요 가능

    def post(self, request, post_id):
        # 좋아요를 누를 게시글을 찾습니다.
        post = get_object_or_404(Post, id=post_id)
        user = request.user

        # 만약 사용자가 이미 이 글에 좋아요를 눌렀다면,
        if post.likes.filter(id=user.id).exists():
            # 좋아요를 취소합니다.
            post.likes.remove(user)
            message = "좋아요 취소"
        else:
            # 좋아요를 누르지 않았다면, 좋아요를 추가합니다.
            post.likes.add(user)
            message = "좋아요 성공"
            
        # 현재 좋아요 개수를 포함하여 응답
        return Response({"message": message, "likes_count": post.likes.count()}, status=status.HTTP_200_OK)
# --- 쪽지 API (API 9.x) ---

# ❗️ [오류 수정] MessageConversationListView와 MessageSendView를 
# ❗️ 하나의 'MessageView'로 통합하여 405 오류 해결

class MessageView(APIView):
    """
    API 명세서 9.1 (GET) & 9.3 (POST) 통합 View
    - GET /community/messages/ (대화방 목록 조회)
    - POST /community/messages/ (쪽지 전송)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        API 명세서 9.1: 대화방 목록 조회
        """
        user = request.user
        involved_messages = Message.objects.filter(Q(sender=user) | Q(receiver=user))
        
        sent_to_users = involved_messages.filter(sender=user).values_list('receiver', flat=True)
        received_from_users = involved_messages.filter(receiver=user).values_list('sender', flat=True)
        
        participant_ids = set(list(sent_to_users) + list(received_from_users))

        conversations = []
        for user_id in participant_ids:
            try:
                participant = User.objects.get(id=user_id)
                latest_message = Message.objects.filter(
                    (Q(sender=user) & Q(receiver=participant)) |
                    (Q(sender=participant) & Q(receiver=user))
                ).latest('sent_at') 
                
                conversations.append({
                    "participant": UserSerializer(participant).data,
                    "latest_message": MessageSerializer(latest_message).data
                })
            except (User.DoesNotExist, Message.DoesNotExist):
                continue

        conversations.sort(key=lambda x: x['latest_message']['sent_at'], reverse=True)
        
        return Response(conversations, status=status.HTTP_200_OK)

    def post(self, request):
        """
        API 명세서 9.3: 쪽지 전송
        """
        sender = request.user
        receiver_username = request.data.get('receiver_username')
        content = request.data.get('content')

        if not receiver_username or not content:
            return Response({"error": "받는 사람과 내용이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            receiver = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            return Response({"error": "해당 사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        message = Message.objects.create(
            sender=sender,
            receiver=receiver,
            content=content
        )
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageDetailView(APIView):
    """
    API 명세서 9.2: 특정 사용자와의 대화 내용 조회
    - GET /community/messages/<str:username>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, username):
        user = request.user
        try:
            participant = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "해당 사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(
            (Q(sender=user) & Q(receiver=participant)) |
            (Q(sender=participant) & Q(receiver=user))
        ).order_by('sent_at')

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)