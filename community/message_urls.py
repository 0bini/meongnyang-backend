# community/message_urls.py
# (새로 만드는 파일)

from django.urls import path
# ❗️ views.py에서 MessageView, MessageDetailView를 가져옵니다.
from .views import MessageView, MessageDetailView

urlpatterns = [
    # 9.1 대화방 목록 조회 (GET) & 9.3 쪽지 전송 (POST)
    # GET, POST /api/v1/messages/
    path(
        '',
        MessageView.as_view(), 
        name='message-list-create'
    ),
    
    # 9.2 대화 내용 조회
    # GET /api/v1/messages/<str:username>/
    path(
        '<str:username>/',
        MessageDetailView.as_view(),
        name='message-detail'
    ),
]