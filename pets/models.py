from django.db import models
from users.models import User # users 앱의 User 모델 import
from django.utils import timezone

# --- Helper 함수 ---
def get_current_date():
    """현재 날짜를 반환하는 함수 (DateField default용)"""
    return timezone.now().date()

# --- Choices 정의 (선택 필드용) ---
SPECIES_CHOICES = [('강아지', '강아지'), ('고양이', '고양이')]
GENDER_CHOICES = [('수컷', '수컷'), ('암컷', '암컷')]

MEAL_TYPES = [('사료', '사료'), ('간식', '간식'), ('특식', '특식'), ('영양제', '영양제')]
ACTIVITY_TYPES = [('산책', '산책'), ('놀이', '놀이'), ('훈련', '훈련'), ('외출', '외출'), ('기타', '기타')]
HEALTH_LOG_TYPES = [('예방접종', '예방접종'), ('병원방문', '병원방문'), ('투약', '투약'), ('기타', '기타')]
CALENDAR_CATEGORIES = [('병원/약', '병원/약'), ('미용', '미용'), ('행사', '행사'), ('기타', '기타')]
CARE_LOG_TYPES = [('양치질', '양치질'), ('빗질', '빗질'), ('목욕', '목욕'), ('발톱깎기', '발톱깎기'), ('기타', '기타')]


# --- 모델 정의 ---

class Pet(models.Model):
    """반려동물 기본 정보 모델"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pets', verbose_name="주인")
    name = models.CharField(max_length=100, verbose_name="이름")
    species = models.CharField(max_length=10, choices=SPECIES_CHOICES, verbose_name="종")
    breed = models.CharField(max_length=100, verbose_name="품종")
    birth_date = models.DateField(verbose_name="생년월일")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="성별")
    is_neutered = models.BooleanField(verbose_name="중성화 여부")
    weight = models.FloatField(verbose_name="체중(kg)")
    profile_photo = models.ImageField(upload_to='pet_profiles/', blank=True, null=True, verbose_name="프로필 사진") # Pillow 필요
    target_activity_minutes = models.IntegerField(default=45, verbose_name="하루 목표 활동량(분)")
    special_notes = models.TextField(blank=True, null=True, verbose_name="건강 특이사항")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.owner.username}의 {self.name}"

class MealLog(models.Model):
    """식사 기록 모델"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='meal_logs')
    log_date = models.DateField(verbose_name='기록 날짜', default=get_current_date)
    food_type = models.CharField(max_length=50, choices=MEAL_TYPES, verbose_name='종류 (사료, 간식 등)')
    food_name = models.CharField(max_length=100, verbose_name="사료/간식 이름")
    quantity_g = models.FloatField(verbose_name="양(g)")
    calorie = models.FloatField(verbose_name="칼로리(kcal)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.log_date} {self.pet.name} 식사: {self.food_name}"

class WalkLog(models.Model):
    """활동(산책) 기록 모델"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='walk_logs')
    log_date = models.DateField(verbose_name='기록 날짜', default=get_current_date)
    log_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES, verbose_name='활동 종류', default='산책')
    duration = models.IntegerField(verbose_name="활동 시간(분)")
    distance = models.FloatField(blank=True, null=True, verbose_name="이동 거리(km, 선택)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.log_date} {self.pet.name} 활동: {self.log_type}"

class HealthLog(models.Model):
    """건강 기록 모델 (병원, 접종 등)"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='health_logs')
    log_date = models.DateField(verbose_name="기록 날짜")
    log_type = models.CharField(max_length=50, choices=HEALTH_LOG_TYPES, verbose_name="기록 종류")
    content = models.TextField(verbose_name="내용")
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="장소 또는 약 이름")
    
    # ❗️ [오류 수정] 500 에러 해결을 위한 'weight' 필드 추가
    weight = models.FloatField(blank=True, null=True, verbose_name='당시 체중 (kg)')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.log_date} {self.pet.name} 건강 기록: {self.log_type}"

class CalendarSchedule(models.Model):
    """캘린더 일정 모델"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='schedules')
    schedule_date = models.DateField(verbose_name="일정 날짜")
    content = models.CharField(max_length=200, verbose_name="일정 내용")
    category = models.CharField(max_length=50, choices=CALENDAR_CATEGORIES, verbose_name="카테고리")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pet.name} 일정 ({self.schedule_date}) - {self.content}"

class CareLog(models.Model):
    """오늘의 케어 리스트 항목 모델"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='care_logs')
    log_date = models.DateField(verbose_name='해당 날짜', default=get_current_date)
    content = models.CharField(max_length=200, verbose_name="할 일 내용") # 디자인상 자유 입력
    is_complete = models.BooleanField(default=False, verbose_name="완료 여부")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('pet', 'log_date', 'content')

    def __str__(self):
        return f"{self.pet.name} 케어 ({self.log_date}) - {self.content}"

# ❗️ [오류 수정] makemigrations ImportError 해결을 위한 클래스 추가
class BcsCheckupResult(models.Model):
    """BCS 자가 진단 결과 저장 모델"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='bcs_results')
    answers = models.JSONField(verbose_name="답변 목록") # 예: [1, 2, 1]
    
    # --- ⬇️ [수정] default 값을 추가합니다. ⬇️ ---
    stage_number = models.IntegerField(verbose_name="진단 단계 (숫자)", default=5) 
    stage_text = models.CharField(max_length=100, verbose_name="진단 결과 (텍스트)", default="이상적")
    # --- ⬆️ [수정] ---

    checkup_date = models.DateTimeField(auto_now_add=True, verbose_name="진단 일시")

    def __str__(self):
        # [수정] __str__도 새 필드를 반영하도록 변경
        return f"{self.pet.name} BCS 결과 ({self.checkup_date.date()}) - {self.stage_number}단계: {self.stage_text}"

