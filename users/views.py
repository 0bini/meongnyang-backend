# users/views.py
from rest_framework import status, generics, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model

# 방금 우리가 만든 Serializer들을 가져옵니다.
from .serializers import UserRegisterSerializer, UserSerializer, UserProfileSerializer, UserSearchSerializer

User = get_user_model()

class RegisterView(APIView):
    """
    API 명세서 2.1: 회원가입
    """
    serializer_class = UserRegisterSerializer

    def post(self, request):
        # 1. 프론트엔드에서 보낸 데이터(request.data)를 Serializer에 넣습니다.
        serializer = self.serializer_class(data=request.data)
        
        # 2. Serializer의 validate 기능으로 데이터 유효성을 검사합니다.
        if serializer.is_valid(raise_exception=True):
            # 3. 유효성 검사를 통과하면, serializer의 save()를 호출합니다.
            # (이때 Serializer의 create 메소드가 실행되어 유저가 생성됩니다.)
            serializer.save()
            
            # 4. API 명세서대로 성공 응답을 보냅니다.
            return Response({"message": "회원가입이 성공적으로 완료되었습니다."}, status=status.HTTP_201_CREATED)
        
        # is_valid에서 raise_exception=True로 설정했기 때문에,
        # 유효성 검사 실패 시(중복 등) 자동으로 400 Bad Request 응답을 보냅니다.
        # 이 코드는 사실상 실행되지 않지만, 만약을 위해 남겨둡니다.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """
    API 명세서 2.2: 로그인
    """
    def post(self, request):
        # 1. 프론트엔드에서 보낸 아이디와 비밀번호를 받습니다.
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({"error": "아이디와 비밀번호를 모두 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Django의 authenticate 함수로 사용자 인증을 시도합니다.
        user = authenticate(username=username, password=password)

        # 3. 인증에 성공했다면 (user가 None이 아니라면)
        if user is not None:
            # 4. JWT 토큰(access, refresh)을 생성합니다.
            refresh = RefreshToken.for_user(user)
            
            # 5. API 명세서 2.2 Response 형식에 맞춰 응답 데이터를 구성합니다.
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data  # UserSerializer 사용
            }, status=status.HTTP_200_OK)
        else:
            # 6. 인증에 실패했다면 (아이디 또는 비밀번호 불일치)
            return Response({"error": "아이디 또는 비밀번호가 일치하지 않습니다."}, status=status.HTTP_401_UNAUTHORIZED)
        
        # ⬇️ [추가] API 2.3 (계정 설정 조회) & 2.4 (계정 설정 수정) & 2.5 (회원 탈퇴)
class UserProfileView(generics.RetrieveUpdateDestroyAPIView):
    """
    (API 2.3) 계정 설정 조회 (GET)
    (API 2.4) 계정 설정 수정 (PUT, PATCH)
    (API 2.5) 회원 탈퇴 (DELETE)
    - 요청자 본인(request.user)의 정보만 처리합니다.
    """
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated] # ⭐️ 인증된 사용자만 접근 가능

    def get_object(self):
        """
        URL에 pk 대신, 요청을 보낸 사용자 본인의 객체를 반환합니다.
        """
        return self.request.user

    def perform_destroy(self, instance):
        """
        회원 탈퇴 시 DB에서 완전히 삭제합니다. (Hard Delete)
        """
        instance.delete()

    # GET, PUT, PATCH, DELETE은 RetrieveUpdateDestroyAPIView가 자동으로 처리합니다.
    # (username은 serializer에서 read_only로 설정했기 때문에 수정되지 않습니다.)


# ⬇️ [추가] API 2.5 (회원 탈퇴)
class UnregisterView(generics.DestroyAPIView):
    """
    (API 2.5) 회원 탈퇴 (DELETE)
    - 요청자 본인(request.user)의 계정만 삭제(비활성화)합니다.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated] # ⭐️ 인증된 사용자만 접근 가능

    def get_object(self):
        """
        삭제할 객체로 요청자 본인을 반환합니다.
        """
        return self.request.user

    def perform_destroy(self, instance):
        """
        회원 탈퇴 시 DB에서 완전히 삭제합니다. (Hard Delete)
        """
        instance.delete()


# ⬇️ [추가] API 2.6 (사용자 검색)
class UserSearchView(generics.ListAPIView):
    """
    (API 2.6) 사용자 검색 (GET)
    - 쿼리 파라미터 'search'로 검색합니다. (ex: /api/v1/users/search/?search=검색어)
    """
    queryset = User.objects.filter(is_active=True) # 활성화된 사용자만 검색
    serializer_class = UserSearchSerializer
    permission_classes = [permissions.IsAuthenticated] # ⭐️ 로그인한 사용자만 검색 가능
    
    # ⭐️ DRF SearchFilter 사용 설정
    filter_backends = [filters.SearchFilter]
    
    # ⭐️ 'username' 또는 'nickname' 필드를 기준으로 검색
    search_fields = ['username', 'nickname']