from rest_framework import viewsets

from comptes.models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR, ROLE_CHEF_SERVICE
from comptes.permissions import role_requis
from decomptes.models import journaliser
from .models import Absence
from .serializers import AbsenceSerializer


class AbsenceViewSet(viewsets.ModelViewSet):
    serializer_class = AbsenceSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)()]
        return [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR, ROLE_CHEF_SERVICE)()]

    def get_queryset(self):
        utilisateur = self.request.user
        base = Absence.objects.order_by('-date_debut')
        if utilisateur.role == ROLE_CHEF_SERVICE:
            return base.filter(agent__service_id=utilisateur.service_id)
        return base

    def perform_create(self, serializer):
        absence = serializer.save()
        journaliser(
            self.request.user, "Création d'une absence",
            cible=f"Absence:{absence.id}",
            details=f"Agent {absence.agent_id}, du {absence.date_debut} au {absence.date_fin}.",
        )

    def perform_update(self, serializer):
        absence = serializer.save()
        journaliser(
            self.request.user, "Modification d'une absence",
            cible=f"Absence:{absence.id}",
            details=f"Agent {absence.agent_id}, du {absence.date_debut} au {absence.date_fin}.",
        )

    def perform_destroy(self, instance):
        journaliser(
            self.request.user, "Suppression d'une absence",
            cible=f"Absence:{instance.id}",
            details=f"Agent {instance.agent_id}, du {instance.date_debut} au {instance.date_fin}.",
        )
        instance.delete()
