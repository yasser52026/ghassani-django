from django.urls import path
from .views import GrillePlanningView, EnregistrerGrilleView, CalculerView, MesGardesView, ExporterPlanningWordView

urlpatterns = [
    path('mes-gardes/', MesGardesView.as_view()),
    path('<int:service_id>/<int:annee>/<int:mois>/', GrillePlanningView.as_view()),
    path('<int:planning_id>/enregistrer/', EnregistrerGrilleView.as_view()),
    path('<int:planning_id>/calculer/', CalculerView.as_view()),
    path('<int:planning_id>/export-word/', ExporterPlanningWordView.as_view()),
]
