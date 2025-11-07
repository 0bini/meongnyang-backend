# community/urls.py
# (기존 파일 수정)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PostViewSet, 
    CommentViewSet, 
    LikeView,
    # ❗️ [수정] 쪽지 뷰들은 여기서 더 이상 사용하지 않으므로 삭제
    # MessageView, 
    # MessageDetailView
)

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
    
    # --- 게시글/댓글/좋아요 (API 8.x) ---
    path(
        'posts/<int:post_id>/comments/', 
        CommentViewSet.as_view({'get': 'list', 'post': 'create'}), 
        name='post-comment'
    ),
    path(
        'posts/<int:post_id>/like/', 
        LikeView.as_view(), 
        name='post-like'
    ),

    # --- [수정] 쪽지 API (API 9.x) URL 부분 ---
    # ❗️ 이 부분을 통째로 삭제 (message_urls.py로 이동했음)
]