# notifications/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer

class NotificationListView(generics.ListAPIView):
    """
    API 명세서 10.1: 알림 목록 조회 (GET /notifications/)
    - 로그인한 본인의 알림 목록만 반환합니다.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated] # ❗️ 로그인 필수

    def get_queryset(self):
        # 1. 요청을 보낸 사용자(request.user)의 알림만 필터링
        queryset = Notification.objects.filter(user=self.request.user)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # 2. 읽지 않은 알림 개수 계산
        unread_count = queryset.filter(is_read=False).count()
        
        # 3. API 명세서 10.1 형식에 맞게 응답 데이터 재구성
        response_data = {
            "unread_count": unread_count,
            "notifications": serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class NotificationReadView(APIView):
    """
    API 명세서 10.2: 특정 알림 읽음 처리 (POST /notifications/<int:notification_id>/read/)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id):
        try:
            # 1. 알림 ID로 객체를 찾되, 본인(request.user)의 알림이 맞는지 확인
            notification = Notification.objects.get(id=notification_id, user=request.user)
            
            # 2. 이미 읽었다면 추가 작업 없이 성공 응답
            if notification.is_read:
                return Response({"message": "이미 읽음 처리된 알림입니다."}, status=status.HTTP_200_OK)
                
            # 3. 읽음 처리 (is_read=True)
            notification.is_read = True
            notification.save()
            
            return Response({"message": "알림을 읽음 처리했습니다."}, status=status.HTTP_200_OK)
            
        except Notification.DoesNotExist:
            return Response({"error": "알림을 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)


class NotificationReadAllView(APIView):
    """
    API 명세서 10.2: 모든 알림 읽음 처리 (POST /notifications/read-all/)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # 1. 로그인한 사용자의 "읽지 않은(is_read=False)" 알림만 모두 찾음
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False)
        
        # 2. 읽지 않은 알림이 없으면
        if not unread_notifications.exists():
            return Response({"message": "새로운 알림이 없습니다."}, status=status.HTTP_200_OK)

        # 3. 모두 읽음 처리 (update() 메서드로 한 번에 처리)
        count = unread_notifications.update(is_read=True)
        
        return Response({"message": f"총 {count}개의 알림을 모두 읽음 처리했습니다."}, status=status.HTTP_200_OK)