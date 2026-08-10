from django.urls import path
from .views import GrillePlanningView, EnregistrerGrilleView, CalculerView

urlpatterns = [
    path('<int:service_id>/<int:annee>/<int:mois>/', GrillePlanningView.as_view()),
    path('<int:planning_id>/enregistrer/', EnregistrerGrilleView.as_view()),
    path('<int:planning_id>/calculer/', CalculerView.as_view()),
]
