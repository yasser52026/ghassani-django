from rest_framework import viewsets

from comptes.models import ROLE_ADMIN
from comptes.permissions import role_requis
from .models import Service, Poste
from .serializers import ServiceSerializer, PosteSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by('nom')
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return []


class PosteViewSet(viewsets.ModelViewSet):
    queryset = Poste.objects.all()
    serializer_class = PosteSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return []
