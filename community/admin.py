# community/admin.py
from django.contrib import admin
# .models 파일에서 우리가 만든 모든 모델을 가져옵니다.
from .models import Post, Comment, Message

# 가져온 모델들을 관리자 페이지에 등록합니다.
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Message)

