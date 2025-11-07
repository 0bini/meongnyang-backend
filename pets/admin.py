from django.contrib import admin
# ❗️ [오류 수정] 모든 모델을 여기서 import 하지 않습니다.

# ❗️ admin.site.register 데코레이터를 사용하거나,
# ❗️ 필요한 모델만 import 하는 방식으로 변경합니다.

from .models import Pet, MealLog, WalkLog, HealthLog, CalendarSchedule, CareLog, BcsCheckupResult

admin.site.register(Pet)
admin.site.register(MealLog)
admin.site.register(WalkLog)
admin.site.register(HealthLog)
admin.site.register(CalendarSchedule)
admin.site.register(CareLog)
admin.site.register(BcsCheckupResult)