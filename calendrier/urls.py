from rest_framework.routers import DefaultRouter
from .views import JourFerieViewSet, PeriodeRamadanViewSet, BaremeViewSet

router = DefaultRouter()
router.register('jours-feries', JourFerieViewSet, basename='jours-feries')
router.register('ramadan', PeriodeRamadanViewSet, basename='ramadan')
router.register('baremes', BaremeViewSet, basename='baremes')

urlpatterns = router.urls
