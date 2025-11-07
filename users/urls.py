# users/urls.py
from django.urls import path
# ⬇️ 방금 우리가 views.py에 만든 RegisterView와 LoginView를 가져옵니다.
from .views import RegisterView, LoginView, UserProfileView, UnregisterView, UserSearchView

urlpatterns = [
    # 1. API 명세서 2.1 회원가입
    path('register/', RegisterView.as_view(), name='register'),
    
    # 2. API 명세서 2.2 로그인
    path('login/', LoginView.as_view(), name='login'),

    # ❗️ (API 명세서 2.3 & 2.4) 계정 설정 (조회/수정)
    # -> /api/v1/users/profile/
    path('profile/', UserProfileView.as_view(), name='profile'), # ⭐️ 주석 해제 및 뷰 연결

    # ❗️ (API 명세서 2.5) 회원 탈퇴
    # -> /api/v1/users/unregister/
    path('unregister/', UnregisterView.as_view(), name='unregister'), # ⭐️ 주석 해제 및 뷰 연결
    
    # ❗️ (API 명세서 2.6) 사용자 검색
    # -> /api/v1/users/search/
    path('search/', UserSearchView.as_view(), name='user-search'), # ⭐️ 주석 해제 및 뷰 연결
]

# ❗️ 나머지 기능(profile, unregister, search)의 View는
# ❗️ 아직 만들지 않았으므로, 일단 주석 상태로 둡니다.

