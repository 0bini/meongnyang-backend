from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
# ❗️ [수정] HealthLog, BcsCheckupResult 등 모든 모델 import
from .models import Pet, CareLog, CalendarSchedule, HealthLog, WalkLog, BcsCheckupResult
# ❗️ [수정] HealthLogSerializer, BcsCheckupResultSerializer 등 모든 시리얼라이저 import
from .serializers import (
    PetSerializer, CareLogSerializer, CalendarScheduleSerializer, 
    WalkLogSerializer, HealthLogSerializer, BcsCheckupResultSerializer
)
from django.utils import timezone
from django.db.models import Sum, Avg
from datetime import date # d_day 계산을 위해 import
from rest_framework.exceptions import ValidationError # 예외 처리를 위해 import

# --- 권한 설정 ---
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자만 수정/삭제할 수 있도록 하는 커스텀 권한입니다.
    """
    def has_object_permission(self, request, view, obj):
        # 읽기 요청(GET, HEAD, OPTIONS)은 항상 허용합니다.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 쓰기 요청(POST, PUT, DELETE)은 객체의 소유자와
        # 요청을 보낸 사용자(request.user)가 동일한 경우에만 허용합니다.
        
        # Pet 모델의 소유자는 'owner' 필드입니다.
        if isinstance(obj, Pet):
            return obj.owner == request.user
        # 다른 모델(CareLog, CalendarSchedule 등)의 소유자는 'pet.owner'를 통해 확인합니다.
        # ❗️ BcsCheckupResult도 pet 필드를 통해 소유자를 확인하도록 추가
        if hasattr(obj, 'pet'):
            return obj.pet.owner == request.user
            
        return False

# --- Pet API (API 3.x) ---
class PetViewSet(viewsets.ModelViewSet):
    """
    API 명세서 3.1, 3.2, 3.3: 반려동물 정보의 생성(C), 조회(R), 수정(U), 삭제(D)
    """
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    # 인증된 사용자만 이 ViewSet에 접근할 수 있습니다.
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """
        이 요청을 보낸 사용자(로그인한 사용자)가 소유한 반려동물 목록만 반환합니다.
        """
        user = self.request.user
        return Pet.objects.filter(owner=user)

    def perform_create(self, serializer):
        """
        POST 요청으로 새로운 반려동물을 생성할 때,
        'owner' 필드를 요청을 보낸 사용자로 자동 설정합니다.
        """
        serializer.save(owner=self.request.user)

# --- Dashboard & CareLog API (API 4.x) ---

class CareLogViewSet(viewsets.ModelViewSet):
    """
    API 명세서 4.2, 4.3: 오늘의 케어리스트(CareLog) 항목 관리(CRUD) ViewSet
    - POST /pets/care-list/{pet_id}/
    - PUT /pets/carelogs/items/{item_id}/
    - DELETE /pets/carelogs/items/{item_id}/
    """
    queryset = CareLog.objects.all()
    serializer_class = CareLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # 소유자만 관리 가능

    def get_queryset(self):
        """
        이 요청을 보낸 사용자가 소유한 케어로그만 반환합니다.
        """
        user = self.request.user
        return CareLog.objects.filter(pet__owner=user)

    def perform_create(self, serializer):
        """
        POST 요청 시, pet 정보를 URL에서 가져와 자동으로 저장합니다.
        log_date는 오늘 날짜로 자동 설정합니다.
        
        [수정 완료] URL(.../care-list/<int:pet_id>/)에서 pet_id를 받아옵니다.
        """
        try:
            # URL kwarg에서 pet_id를 가져옵니다.
            pet_id = self.kwargs.get('pet_id')
            if not pet_id:
                # /pets/carelogs/items/ 로 POST 요청이 올 경우 (ViewSet 기본 동작)
                # API 명세서 4.2와 맞지 않으므로, pet_id를 request.data에서 가져오도록 시도
                pet_id = self.request.data.get('pet')
                if not pet_id:
                     raise ValidationError("pet_id가 요청에 포함되지 않았습니다.")
            
            pet = Pet.objects.get(id=pet_id, owner=self.request.user)
            serializer.save(pet=pet, log_date=timezone.now().date())
        except Pet.DoesNotExist:
            raise ValidationError("유효한 반려동물이 아니거나, 본인의 반려동물이 아닙니다.")
        except KeyError:
            raise ValidationError("URL에서 pet_id를 찾을 수 없습니다. URL 설정이 'care-list/<int:pet_id>/' 형태가 맞는지 확인하세요.")
        except Exception as e:
            raise ValidationError(f"예상치 못한 오류 발생: {e}")


class DashboardView(APIView):
    """
    API 명세서 4.1: 메인 대시보드 정보 조회 View
    - GET /dashboard/<int:pet_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pet_id):
        # 1. 요청 보낸 사용자가 pet_id의 주인인지 확인
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()

        # 2. 오늘의 케어 리스트 (API 4.1 - care_list)
        care_items = CareLog.objects.filter(pet=pet, log_date=today)
        care_serializer = CareLogSerializer(care_items, many=True)
        total_care_count = care_items.count()
        completed_care_count = care_items.filter(is_complete=True).count()
        care_list_data = {
            "items": care_serializer.data,
            "completion_rate": (completed_care_count / total_care_count) if total_care_count > 0 else 0
        }

        # 3. 다가오는 일정 (API 4.1 - upcoming_schedules)
        upcoming_schedules = CalendarSchedule.objects.filter(
            pet=pet, 
            schedule_date__gte=today # 오늘 날짜(today)와 같거나 큰(gte) 일정
        ).order_by('schedule_date')[:2] # 가까운 순서대로 2개만
        schedule_serializer = CalendarScheduleSerializer(upcoming_schedules, many=True)

        # 4. 건강 추세 (API 4.1 - health_trend)
        # HealthLog에서 가장 최근 체중을 가져옵니다.
        last_health_log = HealthLog.objects.filter(pet=pet, weight__isnull=False).order_by('-log_date').first()
        last_weight = last_health_log.weight if last_health_log else pet.weight # 최근 기록이 없으면 Pet의 기본 체중
        
        # ❗️ [개선] HealthLog에서 최근 12개월간의 월별 평균 체중을 계산합니다.
        # 이 로직은 실제로는 더 복잡하지만, 여기서는 간단한 예시로 최근 2개 기록을 보여줍니다.
        recent_weights = HealthLog.objects.filter(pet=pet, weight__isnull=False).order_by('-log_date')[:2]
        
        weight_graph_data = [
            {"month": log.log_date.strftime("%m월"), "weight": log.weight} for log in reversed(recent_weights)
        ]
        if not weight_graph_data: # 건강 기록이 없을 경우
             weight_graph_data = [
                { "month": today.strftime("%m월"), "weight": pet.weight }
             ]

        # 최근 체중 변화 계산 로직 (예시)
        recent_change_str = "변동 없음"
        if len(recent_weights) >= 2:
            change = recent_weights[0].weight - recent_weights[1].weight
            recent_change_str = f"{'+' if change > 0 else ''}{change:.1f}kg"
        elif last_health_log:
             recent_change_str = f"{last_health_log.weight}kg (최근)"
        
        health_trend_data = {
            "recent_change": recent_change_str, 
            "graph_data": weight_graph_data
        }

        # 5. 음식 가이드 (API 4.1 - food_guide)
        # (이 부분은 DB에 별도 Food 모델로 저장해두고 가져오는 것이 좋습니다.)
        food_guide_data = {
            "good_foods": [
                { "id": 1, "name": "당근, 고구마, 브로콜리", "description": "적정량 주면 소화에 좋아요. (소량만)" },
                { "id": 2, "name": "사과, 배, 바나나", "description": "씨와 껍질을 벗겨 반드시 제거하고 주세요." }
            ],
            "bad_foods": [
                { "id": 3, "name": "초콜릿", "description": "테오브로민 성분은 매우 치명적이에요." },
                { "id": 4, "name": "양파, 마늘, 파", "description": "적혈구를 파괴하여 빈혈을 유발해요." }
            ]
        }

        # 6. 모든 데이터를 API 명세서 형식에 맞춰 조합
        response_data = {
            "care_list": care_list_data,
            "upcoming_schedules": schedule_serializer.data,
            "health_trend": health_trend_data,
            "food_guide": food_guide_data
        }

        return Response(response_data, status=status.HTTP_200_OK)

# --- Activity API (API 5.x) ---

class WalkLogViewSet(viewsets.ModelViewSet):
    """
    API 명세서 5.2, 5.3: 활동 기록(WalkLog) 관리(CRUD) ViewSet
    - POST /pets/activities/logs/{pet_id}/
    - PUT /pets/activities/logs/{log_id}/
    - DELETE /pets/activities/logs/{log_id}/
    """
    queryset = WalkLog.objects.all()
    serializer_class = WalkLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # 소유자만 관리 가능

    def get_queryset(self):
        """
        이 요청을 보낸 사용자가 소유한 반려동물의 활동 기록만 반환합니다.
        """
        user = self.request.user
        return WalkLog.objects.filter(pet__owner=user)

    def perform_create(self, serializer):
        """
        POST 요청 시, pet 정보를 URL에서 가져와 자동으로 저장합니다.
        """
        try:
            pet = Pet.objects.get(id=self.kwargs['pet_id'], owner=self.request.user)
            # API 5.2 Request Body에는 log_date가 포함되어 있으므로, 
            # serializer가 받은 값을 그대로 씁니다.
            serializer.save(pet=pet)
        except Pet.DoesNotExist:
            raise ValidationError("유효한 반려동물이 아니거나, 본인의 반려동물이 아닙니다.")
        except KeyError:
            raise ValidationError("URL에서 pet_id를 찾을 수 없습니다.")


class ActivityPageView(APIView):
    """
    API 명세서 5.1: 활동 페이지 정보 조회 View
    - GET /pets/activities/{pet_id}/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pet_id):
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()

        # 1. 오늘의 활동 요약 (today_summary)
        today_logs = WalkLog.objects.filter(pet=pet, log_date=today)
        today_summary_agg = today_logs.aggregate(
            total_duration=Sum('duration'),
            total_distance=Sum('distance')
        )
        today_summary = {
            "duration": today_summary_agg['total_duration'] or 0,
            "distance": today_summary_agg['total_distance'] or 0
        }

        # 2. 주간 활동 분석 (weekly_analysis)
        # (실제로는 7일치 데이터를 조회해서 합산해야 합니다.)
        # ❗️ [개선] 지난 7일간의 날짜별 총 활동 시간(duration)을 계산
        weekly_data = []
        for i in range(6, -1, -1): # 6일 전 ~ 오늘
            day = today - timezone.timedelta(days=i)
            daily_duration = WalkLog.objects.filter(pet=pet, log_date=day).aggregate(total=Sum('duration'))['total']
            weekly_data.append({
                "day": day.strftime("%a"), # 예: "Mon"
                "duration": daily_duration or 0
            })
        
        # 3. 최근 산책 기록 (recent_logs)
        recent_logs = WalkLog.objects.filter(pet=pet).order_by('-log_date', '-created_at')[:5] # 최근 5개
        logs_serializer = WalkLogSerializer(recent_logs, many=True)

        # 4. 모든 데이터를 API 명세서 형식에 맞춰 조합
        response_data = {
            "today_summary": today_summary,
            "weekly_analysis": weekly_data, # ❗️ API 명세서와 형식이 다름 (개선)
            "recent_logs": logs_serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)

# --- Calendar API (API 6.x) --- [❗️ 2-B 단계: 이 코드 블록이 새로 추가되었습니다!]

class CalendarScheduleViewSet(viewsets.ModelViewSet):
    """
    API 명세서 6.2, 6.3: 캘린더 일정(CalendarSchedule) 관리(CRUD) ViewSet
    - POST /pets/calendar/schedules/{pet_id}/
    - PUT /pets/calendar/schedules/{schedule_id}/
    - DELETE /pets/calendar/schedules/{schedule_id}/
    """
    queryset = CalendarSchedule.objects.all()
    serializer_class = CalendarScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # 소유자만 관리 가능

    def get_queryset(self):
        """
        이 요청을 보낸 사용자가 소유한 반려동물의 일정만 반환합니다.
        """
        user = self.request.user
        return CalendarSchedule.objects.filter(pet__owner=user)

    def perform_create(self, serializer):
        """
        POST 요청 시, pet 정보를 URL에서 가져와 자동으로 저장합니다.
        """
        try:
            pet = Pet.objects.get(id=self.kwargs['pet_id'], owner=self.request.user)
            # API 6.2 Request Body에는 schedule_date가 포함되어 있으므로,
            # serializer가 받은 값을 그대로 씁니다.
            serializer.save(pet=pet)
        except Pet.DoesNotExist:
            raise ValidationError("유효한 반려동물이 아니거나, 본인의 반려동물이 아닙니다.")
        except KeyError:
            raise ValidationError("URL에서 pet_id를 찾을 수 없습니다.")

class CalendarScheduleListView(APIView):
    """
    API 명세서 6.1: 월별 일정 조회 View
    - GET /pets/calendar/{pet_id}/?year=YYYY&month=MM
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pet_id):
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 쿼리 파라미터에서 year와 month를 가져옵니다.
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            return Response({"error": "year와 month 쿼리 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response({"error": "year와 month는 숫자여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 해당 년도/월의 일정만 필터링
        schedules = CalendarSchedule.objects.filter(
            pet=pet,
            schedule_date__year=year,
            schedule_date__month=month
        ).order_by('schedule_date')
        
        serializer = CalendarScheduleSerializer(schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
# --- Health & BCS API (API 7.x) --- [❗️ 2단계: 이 코드 블록을 새로 추가!]

class HealthLogViewSet(viewsets.ModelViewSet):
    """
    API 명세서 7.2: 건강 기록(HealthLog) 관리(CRUD) ViewSet
    - POST /pets/health/logs/{pet_id}/
    - PUT /pets/health/logs/{log_id}/
    - DELETE /pets/health/logs/{log_id}/
    """
    queryset = HealthLog.objects.all()
    serializer_class = HealthLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # 소유자만 관리 가능

    def get_queryset(self):
        """
        이 요청을 보낸 사용자가 소유한 반려동물의 건강 기록만 반환합니다.
        """
        user = self.request.user
        return HealthLog.objects.filter(pet__owner=user)

    def perform_create(self, serializer):
        """
        POST 요청 시, pet 정보를 URL에서 가져와 자동으로 저장합니다.
        """
        try:
            pet = Pet.objects.get(id=self.kwargs['pet_id'], owner=self.request.user)
            # API 7.2 Request Body의 데이터를 그대로 사용하여 저장
            serializer.save(pet=pet)
        except Pet.DoesNotExist:
            raise ValidationError("유효한 반려동물이 아니거나, 본인의 반려동물이 아닙니다.")
        except KeyError:
            raise ValidationError("URL에서 pet_id를 찾을 수 없습니다.")

class HealthPageView(APIView):
    """
    API 명세서 7.1: 건강 페이지 정보 조회 View
    - GET /pets/health/{pet_id}/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pet_id):
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 1. 체중 변화 그래프 데이터 (HealthLog에서 체중 기록 조회)
        weight_logs = HealthLog.objects.filter(pet=pet, weight__isnull=False).order_by('log_date')
        weight_graph_data = [
            {"date": log.log_date, "weight": log.weight} 
            for log in weight_logs
        ]
        
        # 2. 최근 건강 기록 리스트
        recent_health_logs = HealthLog.objects.filter(pet=pet).order_by('-log_date')[:5] # 최근 5개
        logs_serializer = HealthLogSerializer(recent_health_logs, many=True)
        
        # 3. 반려동물 기본 건강 정보
        pet_info = {
            "name": pet.name,
            "breed": pet.breed,
            "current_weight": pet.weight,
            "age": (date.today() - pet.birth_date).days // 365, # 간단한 나이 계산
            "bcs": BcsCheckupResult.objects.filter(pet=pet).last().result_stage if BcsCheckupResult.objects.filter(pet=pet).exists() else "측정 안함"
        }

        response_data = {
            "pet_info": pet_info,
            "weight_graph": weight_graph_data,
            "recent_health_logs": logs_serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

class AiCheckupView(APIView):
    """
    API 명세서 7.3: AI 건강 분석 View
    - POST /pets/health/ai-checkup/{pet_id}/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pet_id):
        # 1. 반려동물 존재 확인
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 2. 프론트엔드에서 보낸 증상 목록(symptoms)과 위치(location) 받기
        symptoms = request.data.get('symptoms', []) # 예: ["구토", "설사"]
        user_location = request.data.get('location') # 예: {"lat": 33.450, "lng": 126.570}

        if not symptoms:
            return Response({"error": "증상을 선택해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. (가상) AI 모델(LLM API 등) 호출
        # prompt = f"{pet.species} {pet.age}살 {pet.breed}이(가) {', '.join(symptoms)} 증상을 보입니다. 의심 질환과 대처 방안을 알려줘."
        # ai_response = call_my_llm_api(prompt) 
        
        # 4. (가상) 위치 기반 주변 병원 검색
        # clinics_list = search_nearby_clinics(user_location)
        
        # 5. 예시 응답 반환
        response_data = {
          "analysis_result": {
            "suspected_issue": "복통/복부 팽만 (예시)",
            "recommendation": "우선 금식을 시키고, ... 수의사와 상담하세요. (예시)"
          },
          "nearby_clinics": [
            { "id": 1, "name": "제주 댕냥 동물병원 (예시)", "address": "제주시 연동 123-45", "phone": "064-123-4567", "distance": 1.2 }
          ]
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

class BcsCheckupView(APIView):
    """
    API 명세서 7.4: BCS 자가 진단 View
    - POST /pets/health/bcs-checkup/{pet_id}/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pet_id):
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        answers = request.data.get('answers') # 예: [1, 2, 1]

        # 1. (가상) BCS 진단 로직 수행
        # result_stage = calculate_bcs_stage(answers) 
        result_stage = "6단계 - 다소 과체중 (예시)" # 예시 결과

        # 2. 결과 DB에 저장
        result = BcsCheckupResult.objects.create(
            pet=pet,
            answers=answers,
            result_stage=result_stage
        )
        serializer = BcsCheckupResultSerializer(result)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)