# notifications/urls.py
from django.urls import path
from .views import NotificationListView, NotificationReadView, NotificationReadAllView

urlpatterns = [
    # 10.1 알림 목록 조회
    # GET /api/v1/notifications/
    path('', NotificationListView.as_view(), name='notification-list'),
    
    # 10.2 모든 알림 읽음 처리
    # POST /api/v1/notifications/read-all/
    path('read-all/', NotificationReadAllView.as_view(), name='notification-read-all'),

    # 10.2 특정 알림 읽음 처리
    # POST /api/v1/notifications/<notification_id>/read/
    path('<int:notification_id>/read/', NotificationReadView.as_view(), name='notification-read'),
]