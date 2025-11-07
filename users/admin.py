# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# @admin.register(User) 데코레이터를 사용하여 등록합니다.
# UserAdmin을 상속받아 커스텀 User 모델에 최적화된 관리자 페이지를 만듭니다.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    커스텀 User 모델을 위한 관리자 페이지 설정
    """
    # 관리자 페이지 목록에 보여줄 필드 설정
    list_display = ('username', 'email', 'nickname', 'is_staff')
    
    # UserAdmin의 기본 fieldsets을 사용하되, 
    # 'nickname' 필드를 개인 정보(personal info) 섹션에 추가합니다.
    # UserAdmin.fieldsets는 튜플이므로 리스트로 변환 후 수정해야 합니다.
    fieldsets = list(UserAdmin.fieldsets)
    fieldsets[1] = ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'nickname')})
    fieldsets = tuple(fieldsets)

    # User 생성/수정 페이지에 'nickname' 필드 추가
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'nickname')}),
    )

