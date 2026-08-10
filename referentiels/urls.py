from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, PosteViewSet

router = DefaultRouter()
router.register('services', ServiceViewSet, basename='services')
router.register('postes', PosteViewSet, basename='postes')

urlpatterns = router.urls
