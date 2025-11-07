# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
# ⬇️ UserProfileSerializer에서 사용하므로 이건 남겨둡니다.
from django.contrib.auth.password_validation import validate_password 

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    """
    API 명세서 2.1: 회원가입을 위한 Serializer (password2 제거됨)
    """
    # ❗️ [제거] password2 필드 정의 제거
    # password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        # ❗️ [수정] fields에서 'password2' 제거
        fields = ('username', 'password', 'email', 'nickname') 
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
        }

    def validate(self, data):
        """
        비밀번호 검증 로직 (password2 비교 제거)
        """
        # ❗️ [제거] 비밀번호 일치 검증 로직 제거
        # if data['password'] != data['password2']:
        #     raise serializers.ValidationError({"password": "두 비밀번호가 일치하지 않습니다."})
        
        # 이메일 중복 검사 (이건 그대로 둡니다)
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "이미 사용 중인 이메일입니다."})

        return data

    def create(self, validated_data):
        """
        검증을 통과한 데이터로 새로운 사용자를 생성합니다. (비밀번호는 암호화)
        """
        # ❗️ [제거] validated_data에서 password2를 pop하는 코드 제거
        # validated_data.pop('password2')
        
        # User 모델의 create_user 헬퍼 메소드를 사용해 비밀번호를 암호화하여 저장합니다.
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            nickname=validated_data['nickname'],
            password=validated_data['password']
        )
        return user


# ... (이하 UserSerializer, UserProfileSerializer, UserSearchSerializer는 수정할 필요 없음) ...

class UserSerializer(serializers.ModelSerializer):
    """
    API 명세서 2.2: 로그인 응답 등에서 사용자 정보를 보여주기 위한 Serializer
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'nickname', 'email')


class UserProfileSerializer(serializers.ModelSerializer):
    """
    (API 2.3) 계정 설정 조회(GET)
    (API 2.4) 계정 설정 수정(PUT, PATCH)
    """
    new_password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'nickname', 'new_password'] 
        read_only_fields = ['id', 'username']

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.nickname = validated_data.get('nickname', instance.nickname)
        
        new_password = validated_data.get('new_password')
        if new_password:
            instance.set_password(new_password) 
            
        instance.save()
        return instance


class UserSearchSerializer(serializers.ModelSerializer):
    """
    API 명세서 2.6: 사용자 검색을 위한 Serializer
    """
    class Meta:
        model = User
        fields = ['id', 'nickname']