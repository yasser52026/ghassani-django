from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('connexion.html', TemplateView.as_view(template_name='connexion.html')),
    path('index.html', TemplateView.as_view(template_name='index.html')),
    path('', TemplateView.as_view(template_name='index.html')),
    path('api/auth/connexion/', TokenObtainPairView.as_view()),
    path('api/auth/rafraichir/', TokenRefreshView.as_view()),
    path('api/comptes/', include('comptes.urls')),
    path('api/', include('referentiels.urls')),
    path('api/calendrier/', include('calendrier.urls')),
    path('api/absences/', include('absences.urls')),
    path('api/decomptes/', include('decomptes.urls')),
    path('api/plannings/', include('plannings.urls')),
    path('services.html', TemplateView.as_view(template_name='services.html')),
    path('calendrier.html', TemplateView.as_view(template_name='calendrier.html')),
    path('plannings.html', TemplateView.as_view(template_name='plannings.html')),
    path('planning-grille.html', TemplateView.as_view(template_name='planning-grille.html')),
    path('decomptes.html', TemplateView.as_view(template_name='decomptes.html')),
    path('decompte-detail.html', TemplateView.as_view(template_name='decompte-detail.html')),
    path('absences.html', TemplateView.as_view(template_name='absences.html')),
    path('agents.html', TemplateView.as_view(template_name='agents.html')),
    path('demandes.html', TemplateView.as_view(template_name='demandes.html')),
    path('service-detail.html', TemplateView.as_view(template_name='service-detail.html')),
    path('inscription.html', TemplateView.as_view(template_name='inscription.html')),
    path('profil.html', TemplateView.as_view(template_name='profil.html')),
]