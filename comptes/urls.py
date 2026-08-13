from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    UtilisateurViewSet, MoiView, BasculerDisponibiliteView,
    InscriptionView, EnAttenteListView, ValiderInscriptionView, RejeterInscriptionView,
    NotificationsNonLuesView, MarquerNotificationsLuesView,
)

router = DefaultRouter()
router.register('agents', UtilisateurViewSet, basename='agents')

urlpatterns = [
    path('moi/', MoiView.as_view()),
    path('disponibilite/basculer/', BasculerDisponibiliteView.as_view()),
    path('inscription/', InscriptionView.as_view()),
    path('en-attente/', EnAttenteListView.as_view()),
    path('notifications/', NotificationsNonLuesView.as_view()),
    path('notifications/lues/', MarquerNotificationsLuesView.as_view()),
    path('<int:utilisateur_id>/valider/', ValiderInscriptionView.as_view()),
    path('<int:utilisateur_id>/rejeter/', RejeterInscriptionView.as_view()),
] + router.urls
