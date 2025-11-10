from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PetViewSet, 
    DashboardView, 
    CareLogViewSet,
    WalkLogViewSet,
    ActivityPageView,
    # ❗️ [수정] 캘린더 View 2개 import 추가
    CalendarScheduleListView,
    CalendarScheduleViewSet,
    HealthLogViewSet,
    HealthPageView,
    AiCheckupView,
    BcsCheckupView,
    ListMyModelsView
)

# 1. 라우터 생성
router = DefaultRouter()

# 2. PetViewSet과 CareLogViewSet만 라우터에 등록
# (PetViewSet은 /pets/, /pets/{pk}/ 경로들을 자동으로 생성)
router.register(r'pets', PetViewSet, basename='pet')
# (CareLogViewSet은 /carelogs/items/{pk}/ 경로들(수정,삭제)을 자동으로 생성)
router.register(r'carelogs/items', CareLogViewSet, basename='carelog-items')
# ❗️ 캘린더와 활동은 URL 구조가 복잡하므로 라우터에 등록하지 않고 수동으로 정의합니다.


# 3. URL 패턴 수동 정의
urlpatterns = [
    # 3.1 라우터에 등록된 URL들 포함
    path('', include(router.urls)), 
    
    # 3.2 대시보드 (API 4.1)
    # GET /dashboard/<pet_id>/
    path('dashboard/<int:pet_id>/', DashboardView.as_view(), name='dashboard'),
    
    # 3.3 케어리스트 생성 (API 4.2)
    # POST /care-list/<pet_id>/
    path('care-list/<int:pet_id>/', CareLogViewSet.as_view({'post': 'create'}), name='carelog-create'),
    
    # 3.4 활동 페이지 조회 (API 5.1)
    # GET /activities/<pet_id>/
    path('activities/<int:pet_id>/', ActivityPageView.as_view(), name='activity-page'),
    
    # --- 활동 기록(WalkLog) URL 수동 정의 ---
    
    # 3.5 활동 기록 생성 (API 5.2)
    # POST /activities/logs/<pet_id>/
    path('activities/logs/<int:pet_id>/', WalkLogViewSet.as_view({'post': 'create'}), name='walklog-create'), 

    # 3.6 활동 기록 수정/삭제/상세조회 (API 5.3)
    # GET, PUT, DELETE /activities/logs/<log_id>/
    # (pk는 WalkLog의 id를 의미합니다)
    path('activities/logs/<int:pk>/', WalkLogViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='walklog-detail'),

    # --- [수정] 캘린더 API URL 추가 ---

    # 3.7 월별 일정 조회 (API 6.1)
    # GET /calendar/<pet_id>/?year=YYYY&month=MM
    path('calendar/<int:pet_id>/', CalendarScheduleListView.as_view(), name='calendar-list'),
    
    # 3.8 일정 생성 (API 6.2)
    # POST /calendar/schedules/<pet_id>/
    path('calendar/schedules/<int:pet_id>/', CalendarScheduleViewSet.as_view({'post': 'create'}), name='calendar-create'),
    
    # 3.9 일정 수정/삭제/상세조회 (API 6.3)
    # GET, PUT, DELETE /calendar/schedules/<schedule_id>/
    # (pk는 CalendarSchedule의 id를 의미합니다)
    path('calendar/schedules/<int:pk>/', CalendarScheduleViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='calendar-schedule-detail'),

# --- [오류 수정] 건강 & BCS API (API 7.x) URL 수동 정의 ---

    # 7.1 건강 페이지 정보 조회
    path('health/<int:pet_id>/', HealthPageView.as_view(), name='health-page'),
    
    # 7.2 건강 기록 생성 (HealthLogViewSet의 create 액션)
    path('health/logs/<int:pet_id>/', HealthLogViewSet.as_view({'post': 'create'}), name='healthlog-create'),
    
    # 7.2 건강 기록 수정/삭제/상세조회 (HealthLogViewSet의 나머지 액션)
    path('health/logs/<int:pk>/', HealthLogViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='healthlog-detail'),
    
    # 7.3 AI 건강 분석
    path('health/ai-checkup/<int:pet_id>/', AiCheckupView.as_view(), name='ai-checkup'),
    
    # 7.4 BCS 자가 진단
    path('health/bcs-checkup/<int:pet_id>/', BcsCheckupView.as_view(), name='bcs-checkup'),

    # ⬇️ 2. [추가] 이 URL을 맨 아래에 추가 ⬇️
    # GET /api/v1/pets/health/list-my-models/
    path('health/list-my-models/', ListMyModelsView.as_view(), name='list-my-models'),
]