# pets/serializers.py
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Pet, CareLog, CalendarSchedule, WalkLog, HealthLog, BcsCheckupResult, MealLog
from datetime import date

class PetSerializer(serializers.ModelSerializer):
    """
    API 명세서 3.1, 3.2, 3.3: 반려동물 정보의 생성(C), 조회(R), 수정(U)을 담당합니다.
    """
    
    # owner 필드는 직접 입력받는 것이 아니라,
    # 요청을 보낸 사용자(로그인한 사용자)의 정보로 자동 설정할 것입니다.
    # 따라서 '읽기 전용(read_only)'으로 설정하고,
    # 응답(Response) 시에는 보여주되 요청(Request) 시에는 받지 않도록 합니다.
    # User 모델의 닉네임을 보여주도록 설정합니다.
    owner = serializers.ReadOnlyField(source='owner.nickname')

    class Meta:
        model = Pet
        # Pet 모델의 모든 필드를 사용합니다.
        fields = '__all__'
        # id는 자동으로 생성되므로 읽기 전용으로 설정합니다.
        read_only_fields = ('id', 'owner') # owner도 read_only로 추가

    # ❗️ 2. 이 "validate" 함수를 PetSerializer 클래스 안에 추가하세요.
    def validate(self, data):
        """
        데이터 전체를 검증 (중복 등록 방지)
        """
        # '수정(PATCH)'이 아닌 '생성(POST)'일 때만 중복 검사
        if not self.instance:
            user = self.context['request'].user
            pet_name = data.get('name')
            
            if Pet.objects.filter(owner=user, name=pet_name).exists():
                # 이미 존재하면 400 오류 발생
                raise ValidationError("이미 같은 이름의 반려동물이 등록되어 있습니다.")
        
        # 중복이 아니면 데이터를 통과
        return data

class CareLogSerializer(serializers.ModelSerializer):
    """
    API 명세서 4.1 (대시보드)의 'care_list.items'와 
    4.2, 4.3 (케어리스트 관리)를 담당합니다.
    """
    class Meta:
        model = CareLog
        # API 명세서에 따라 필요한 필드만 지정합니다.
        fields = ['id', 'content', 'is_complete']
        read_only_fields = ('id',)

class CalendarScheduleSerializer(serializers.ModelSerializer):
    """
    API 명세서 4.1 (대시보드)의 'upcoming_schedules'와
    6.1, 6.2 (캘린더)를 담당합니다.
    """
    
    # API 명세서 4.1에 'd_day' 필드가 필요하므로,
    # 모델에 없는 필드를 SerializerMethodField로 동적 생성합니다.
    d_day = serializers.SerializerMethodField()

    class Meta:
        model = CalendarSchedule
        # ❗️ [오류 수정] 'schedule_date'로 올바르게 수정
        fields = ['id', 'schedule_date', 'content', 'category', 'd_day'] 
        read_only_fields = ['id', 'd_day']

    def get_d_day(self, obj):
        # 오늘 날짜와 일정 날짜를 비교하여 D-day를 계산합니다.
        today = date.today()
        delta = obj.schedule_date - today
        # 'd_day'는 남은 일수(정수)로 반환합니다.
        return delta.days

class WalkLogSerializer(serializers.ModelSerializer):
    """
    API 명세서 5.x: 활동 기록(WalkLog)을 위한 Serializer
    """
    class Meta:
        model = WalkLog
        # API 5.2의 Request Body와 5.1의 Response에 필요한 필드들을 포함
        fields = ['id', 'log_type', 'duration', 'distance', 'log_date']
        read_only_fields = ['id']
        
class HealthLogSerializer(serializers.ModelSerializer):
    """
    API 명세서 7.2: 건강 기록(HealthLog)을 위한 Serializer
    """
    class Meta:
        model = HealthLog
        # API 7.2의 Request Body와 7.1의 Response에 필요한 필드들
        fields = ['id', 'log_date', 'log_type', 'content', 'location', 'weight']
        read_only_fields = ['id']

class BcsCheckupResultSerializer(serializers.ModelSerializer):
    """
    API 명세서 7.4: BCS 자가 진단 결과를 위한 Serializer
    """
    class Meta:
        model = BcsCheckupResult
        
        # --- ⬇️ [수정] 'result_stage'를 'stage_number', 'stage_text'로 변경 ---
        # API 7.4 Request Body ('answers')와 Response (새 필드들)
        fields = ['id', 'answers', 'stage_number', 'stage_text', 'checkup_date']
        
        # 'stage_number', 'stage_text', 'checkup_date'는 
        # 서버에서 계산하고 저장하므로 읽기 전용
        read_only_fields = ['id', 'stage_number', 'stage_text', 'checkup_date']
        # --- ⬆️ [수정] ---