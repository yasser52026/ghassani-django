from rest_framework import viewsets

from comptes.models import ROLE_ADMIN
from comptes.permissions import role_requis
from decomptes.models import journaliser
from .models import Service, Poste, Equipe
from .serializers import ServiceSerializer, PosteSerializer, EquipeSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by('nom')
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return []

    def perform_create(self, serializer):
        service = serializer.save()
        journaliser(self.request.user, "Création d'un service", cible=f"Service:{service.id}", details=service.nom)

    def perform_update(self, serializer):
        service = serializer.save()
        journaliser(self.request.user, "Modification d'un service", cible=f"Service:{service.id}", details=service.nom)

    def perform_destroy(self, instance):
        journaliser(self.request.user, "Suppression d'un service", cible=f"Service:{instance.id}", details=instance.nom)
        instance.delete()


class PosteViewSet(viewsets.ModelViewSet):
    queryset = Poste.objects.all()
    serializer_class = PosteSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return []

    def perform_create(self, serializer):
        poste = serializer.save()
        journaliser(self.request.user, "Création d'un poste", cible=f"Poste:{poste.id}", details=f"{poste.service.nom} - {poste.type_vacation}")

    def perform_update(self, serializer):
        poste = serializer.save()
        journaliser(self.request.user, "Modification d'un poste", cible=f"Poste:{poste.id}", details=f"{poste.service.nom} - {poste.type_vacation}")

    def perform_destroy(self, instance):
        journaliser(self.request.user, "Suppression d'un poste", cible=f"Poste:{instance.id}", details=f"{instance.service.nom} - {instance.type_vacation}")
        instance.delete()


class EquipeViewSet(viewsets.ModelViewSet):
    queryset = Equipe.objects.all()
    serializer_class = EquipeSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return []

    def perform_create(self, serializer):
        equipe = serializer.save()
        journaliser(self.request.user, "Ajout à l'équipe de rotation", cible=f"Equipe:{equipe.id}", details=f"{equipe.service.nom} - {equipe.agent.nom_complet} (ordre {equipe.ordre})")

    def perform_update(self, serializer):
        equipe = serializer.save()
        journaliser(self.request.user, "Modification de l'ordre de rotation", cible=f"Equipe:{equipe.id}", details=f"{equipe.service.nom} - {equipe.agent.nom_complet} (ordre {equipe.ordre})")

    def perform_destroy(self, instance):
        journaliser(self.request.user, "Retrait de l'équipe de rotation", cible=f"Equipe:{instance.id}", details=f"{instance.service.nom} - {instance.agent.nom_complet}")
        instance.delete()
