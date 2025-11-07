# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    기본 User 모델 확장. username을 ID로 사용하고, nickname 추가.
    email 필드 필수화.
    """
    # Django의 기본 User 모델에는 email과 username(아이디) 필드가 이미 있습니다.
    # 우리는 '닉네임' 필드만 추가해주면 됩니다.
    nickname = models.CharField(max_length=100, unique=True, verbose_name="닉네임")

    # email 필드는 필수 입력 항목으로 변경합니다. (unique=True 추가)
    email = models.EmailField(unique=True, verbose_name="이메일")

    # 이 User 모델은 username을 ID로 사용합니다.
    USERNAME_FIELD = 'username'
    # 관리자 계정 생성 시 필수 입력 항목을 지정합니다. (email, nickname 추가)
    REQUIRED_FIELDS = ['email', 'nickname']

    def __str__(self):
        return self.username # 관리자 페이지 등에서 객체를 문자열로 표시할 때 username 사용
