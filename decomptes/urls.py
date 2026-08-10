from django.urls import path
from .views import DecompteMensuelView, MesDecomptesView, ExportExcelView, ExportPdfView, ValiderDecompteView

urlpatterns = [
    path('mes-decomptes/', MesDecomptesView.as_view()),
    path('<int:service_id>/<int:annee>/<int:mois>/', DecompteMensuelView.as_view()),
    path('<int:service_id>/<int:annee>/<int:mois>/export/excel/', ExportExcelView.as_view()),
    path('<int:service_id>/<int:annee>/<int:mois>/export/pdf/', ExportPdfView.as_view()),
    path('<int:service_id>/<int:annee>/<int:mois>/valider/', ValiderDecompteView.as_view()),
]
