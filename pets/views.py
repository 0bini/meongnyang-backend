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
from django.conf import settings # 1. settings.py의 API 키를 가져오기 위해
import google.generativeai as genai # 2. Google AI 라이브러리
import json # 3. AI 응답(JSON)을 파싱하기 위해
import requests

# --- ⬇️ Kakao API 헬퍼 함수 (AiCheckupView 클래스 *위에* 추가) ⬇️ ---
def search_nearby_clinics(api_key, lat, lng):
    """
    Kakao 키워드 검색 API를 사용해 주변 동물병원을 검색합니다.
    (수정: 프론트엔드 디자인에 맞게 'subtitle' 필드 추가)
    """
    if not api_key:
        # (오류 반환 형식도 디자인에 맞게 수정)
        return [{"id": 0, "name": "API 키 미설정", "subtitle": "Kakao API 키가 서버에 설정되지 않았습니다.", "phone": ""}]

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "query": "동물병원",
        "y": str(lat),
        "x": str(lng),
        "radius": 2000,
        "sort": "distance",
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=3)
        response.raise_for_status() 
        data = response.json()

        clinics = []
        # API 명세서에 맞게 데이터 가공
        for doc in data.get("documents", []):
            
            # --- ⬇️ [수정] 이 부분이 변경되었습니다 ⬇️ ---
            
            # 1. 주소와 전화번호를 가져옵니다.
            address = doc.get("road_address_name") or doc.get("address_name") or "주소 정보 없음"
            phone = doc.get("phone") or "전화번호 정보 없음"
            
            # 2. 디자인이 요구하는 "부제목" 문자열을 생성합니다.
            #    (예: "제주시 연동 123-45 | 064-123-4567")
            subtitle_string = f"{address} | {phone}"

            # 3. 'subtitle' 필드에 담아 반환합니다.
            clinics.append({
                "id": doc.get("id"),
                "name": doc.get("place_name"),
                "subtitle": subtitle_string,  # ⬅️ "부제목" 필드
                "phone": phone,               # ⬅️ "전화" 버튼 클릭 시 사용할 원본 전화번호
                "distance": int(doc.get("distance")) 
            })
            # --- ⬆️ [수정] 여기까지 ⬆️ ---
        
        if not clinics:
            return [{"id": 0, "name": "검색 결과 없음", "subtitle": "2km 이내에 '동물병원' 검색 결과가 없습니다.", "phone": ""}]
        
        return clinics

    except requests.exceptions.RequestException as e:
        return [{"id": 0, "name": "API 호출 오류", "subtitle": f"Kakao API 호출 중 오류 발생: {e}", "phone": ""}]
    except Exception as e:
        return [{"id": 0, "name": "오류", "subtitle": f"처리 중 알 수 없는 오류 발생: {e}", "phone": ""}]

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
        # 1. 반려동물 존재 확인 (기존과 동일)
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 2. 증상 목록 받기 (기존과 동일)
        symptoms = request.data.get('symptoms', []) # 예: ["구토", "설사"]
        user_location = request.data.get('location') # 병원 검색용 (여기선 사용 안 함)

        if not symptoms:
            return Response({"error": "증상을 선택해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # --- ⬇️ [수정] 3. Gemini API 호출 로직 ⬇️ ---
        try:
            # 3-1. API 키 설정
            api_key = settings.GOOGLE_GEMINI_API_KEY
            if not api_key:
                # settings.py에 키가 없거나 환경 변수가 로드되지 않은 경우
                raise ValueError("GOOGLE_GEMINI_API_KEY가 설정되지 않았습니다.")
            
            genai.configure(api_key=api_key)

            # 3-2. AI 모델 및 프롬프트 준비
            model = genai.GenerativeModel('gemini-1.5-flash') # 최신 모델 (gemini-pro도 가능)
            
            # 펫의 나이 계산 (HealthPageView 로직 참고)
            pet_age_days = (date.today() - pet.birth_date).days
            pet_age = pet_age_days // 365 # 간단한 나이 계산
            
            symptoms_str = ", ".join(symptoms) # 리스트를 "구토, 설사" 같은 문자열로 변경

            # AI에게 JSON 형식으로 응답하도록 강력하게 요청하는 프롬프트
            prompt = f"""
            당신은 수의사 역할을 하는 반려동물 건강 AI 어시스턴트입니다.
            아래 반려동물 정보와 주요 증상을 바탕으로, '의심 질환'과 '보호자 대처 방안'을 분석해주세요.

            [반려동물 정보]
            - 종류: {pet.species}
            - 품종: {pet.breed}
            - 나이: {pet_age}살
            - 성별: {pet.gender}
            - 중성화 여부: {'예' if pet.is_neutered else '아니오'}
            - 특이사항: {pet.special_notes or '없음'}

            [주요 증상]
            {symptoms_str}

            [요청]
            분석한 결과를 반드시 다음의 JSON 형식으로만 응답해주세요.
            다른 설명이나 마크다운 표기(```json) 없이 순수한 JSON 객체만 반환해야 합니다.
            'recommendations'는 반드시 3개 이상의 항목으로 구성된 리스트(배열)여야 합니다.

            {{
              "analysis": {{
                "issue_title": "(AI가 판단한 '의심 질환'의 요약 제목. 예: '복합적 문제' 또는 '급성 위장염 의심')",
                "description": "(프론트엔드 디자인의 '의심 질환' 박스에 들어갈 상세 설명. 예: '선택하신 '구토', '설사' 증상은...')"
              }},
              "recommendations": [
                "(프론트엔드 디자인의 '권장 대처 방안' 리스트의 첫 번째 항목. 예: '유산균을 급여하고 식단을 점검해주세요.')",
                "(두 번째 항목. 예: '신선한 물을 마실 수 있도록 수분 섭취를...')"
              ]
            }}
            """

            # 3-3. AI 모델 호출
            ai_response = model.generate_content(prompt)
            
            # 3-4. AI 응답(텍스트)을 JSON 객체로 파싱
            analysis_result = json.loads(ai_response.text)

        except json.JSONDecodeError:
            # AI가 JSON 형식이 아닌 일반 텍스트로 답했을 경우 (예: "죄송합니다...")
            analysis_result = {
                "suspected_issue": "AI 응답 분석 실패",
                "recommendation": f"AI가 JSON 형식이 아닌 응답을 반환했습니다: {ai_response.text}"
            }
        except Exception as e:
            # API 키가 잘못되었거나, 네트워크 오류, 모델 호출 한도 초과 등
            # 500 Internal Server Error로 응답
            return Response({"error": f"AI 분석 중 오류 발생: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # --- ⬆️ [수정] 3. Gemini API 호출 로직 끝 ⬆️ ---
        # 4. (가상) 위치 기반 주변 병원 검색 (기존 로직 유지)
        # --- ⬇️ [수정] 4. (가상) 위치 기반 주변 병원 검색 (실제 API로 교체) ⬇️ ---
        
        clinics_list = []
        kakao_api_key = settings.KAKAO_API_KEY # settings.py에서 키 가져오기
        
        # 1. user_location이 제대로 왔는지 확인
        if not user_location or 'lat' not in user_location or 'lng' not in user_location:
            clinics_list = [{"id": 0, "name": "위치 정보 없음", "address": "사용자 위치 정보(lat, lng)가 전송되지 않았습니다.", "phone": "", "distance": 0}]
        else:
            try:
                # 2. 위도(lat), 경도(lng) 값을 float(숫자)으로 변환
                lat = float(user_location['lat'])
                lng = float(user_location['lng'])
                
                # 3. 위에서 만든 헬퍼 함수 호출!
                clinics_list = search_nearby_clinics(kakao_api_key, lat, lng)
                
            except (ValueError, TypeError):
                 # lat, lng가 숫자가 아닐 경우
                 clinics_list = [{"id": 0, "name": "위치 정보 오류", "address": "위치 정보(lat, lng) 형식이 잘못되었습니다.", "phone": "", "distance": 0}]
        
        # 5. AI 결과와 병원 목록(예시)을 조합하여 최종 응답
        response_data = {
          "analysis_result": analysis_result, # ⬅️ 예시 데이터 대신, AI가 생성한 실제 JSON으로 교체
          "nearby_clinics": clinics_list # ⬅️ 이 부분은 여전히 예시 데이터
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

class BcsCheckupView(APIView):
    """
    API 명세서 7.4: BCS 자가 진단 View
    - POST /pets/health/bcs-checkup/{pet_id}/
    """
    permission_classes = [permissions.IsAuthenticated]

    # class BcsCheckupView(APIView):
# ...
    def post(self, request, pet_id):
        # ... (pet 검증 로직은 동일) ...
        try:
            pet = Pet.objects.get(id=pet_id, owner=request.user)
        except Pet.DoesNotExist:
            return Response({"error": "반려동물 정보를 찾을 수 없거나 권한이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        answers = request.data.get('answers')

        if not answers or not isinstance(answers, list):
            return Response({"error": "유효한 'answers' 리스트가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            total_score = sum(answers)
        except TypeError:
             return Response({"error": "'answers' 리스트는 숫자 값만 포함해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # --- ⬇️ [수정] 점수 구간에 따른 BCS 단계 결정 로직 (구조화) ⬇️ ---
        
        # (참고: 이 점수 구간과 값은 프론트 디자인에 맞춘 예시입니다.)
        stage_number = 5  # 기본값
        stage_text = "이상적"    # 기본값
        
        if total_score <= 3:
            stage_number = 3 # "1-3단계" 중 대표값 (프론트와 협의 필요)
            stage_text = "저체중"
        elif total_score <= 5:
            stage_number = 4
            stage_text = "다소 마름"
        elif total_score <= 7:
            stage_number = 5
            stage_text = "이상적"
        elif total_score <= 9:
            stage_number = 6 # 프론트 디자인의 '6단계' 예시에 맞춤
            stage_text = "다소 과체중"
        else: # total_score > 9
            stage_number = 8 # "8-9단계" 중 대표값
            stage_text = "비만"
        
        # --- ⬆️ [수정] 로직 끝 ⬆️ ---

        # 2. 결과 DB에 저장
        # (❗️ 중요: BcsCheckupResult 모델에 stage_number와 stage_text 필드가 추가되어야 합니다)
        result = BcsCheckupResult.objects.create(
            pet=pet,
            answers=answers,       
            stage_number=stage_number,  # 예: 6
            stage_text=stage_text       # 예: "다소 과체중"
            # 기존 result_stage 필드는 삭제하거나, 
            # result_stage=f"{stage_number}단계 - {stage_text}" 처럼 조합해서 저장
        )
        
        # 3. Serializer를 통해 응답 반환
        # (❗️ 중요: BcsCheckupResultSerializer도 이 새 필드들을 반환하도록 수정되어야 합니다)
        serializer = BcsCheckupResultSerializer(result)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)