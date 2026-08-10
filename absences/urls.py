from rest_framework.routers import DefaultRouter
from .views import AbsenceViewSet

router = DefaultRouter()
router.register('', AbsenceViewSet, basename='absences')

urlpatterns = router.urls
