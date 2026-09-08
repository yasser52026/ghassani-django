from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN
from comptes.permissions import role_requis
from .models import JourFerie, PeriodeRamadan, Bareme
from .serializers import JourFerieSerializer, PeriodeRamadanSerializer, BaremeSerializer


class JourFerieViewSet(viewsets.ModelViewSet):
    queryset = JourFerie.objects.all().order_by('date')
    serializer_class = JourFerieSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return [IsAuthenticated()]


class PeriodeRamadanViewSet(viewsets.ModelViewSet):
    queryset = PeriodeRamadan.objects.all().order_by('-annee')
    serializer_class = PeriodeRamadanSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return [IsAuthenticated()]


class BaremeViewSet(viewsets.ModelViewSet):
    queryset = Bareme.objects.all().order_by('-date_effet')
    serializer_class = BaremeSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return [IsAuthenticated()]
