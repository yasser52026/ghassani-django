from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN
from comptes.permissions import role_requis
from decomptes.models import journaliser
from .models import Service, Poste, Equipe, TYPE_GARDE, TYPE_PERMANENCE, TYPE_ASTREINTE
from .serializers import ServiceSerializer, PosteSerializer, EquipeSerializer

POSTES_PAR_DEFAUT = [
    dict(type_activite=TYPE_GARDE, type_vacation='jour', heure_debut='16:30', heure_fin='20:30', effectif_attendu=1),
    dict(type_activite=TYPE_GARDE, type_vacation='nuit', heure_debut='20:30', heure_fin='08:30', effectif_attendu=1),
    dict(type_activite=TYPE_PERMANENCE, type_vacation='nuit', heure_debut='20:30', heure_fin='08:30', effectif_attendu=1),
    dict(type_activite=TYPE_ASTREINTE, type_vacation='jour', heure_debut='00:00', heure_fin='23:59', effectif_attendu=1),
]


def creer_postes_par_defaut(service):
    """Crée les postes standards (garde jour/nuit, permanence 20:30-08:30,
    astreinte journée) pour un service, en sautant ceux qui existent déjà."""
    existants = set(
        Poste.objects.filter(service=service).values_list('type_activite', 'type_vacation')
    )
    a_creer = [
        Poste(service=service, **defaut)
        for defaut in POSTES_PAR_DEFAUT
        if (defaut['type_activite'], defaut['type_vacation']) not in existants
    ]
    if a_creer:
        Poste.objects.bulk_create(a_creer)
    return len(a_creer)


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by('nom')
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN)()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        service = serializer.save()
        journaliser(self.request.user, "Création d'un service", cible=f"Service:{service.id}", details=service.nom)
        nb_postes = creer_postes_par_defaut(service)
        if nb_postes:
            journaliser(
                self.request.user, "Postes par défaut créés", cible=f"Service:{service.id}",
                details=f"{nb_postes} poste(s) standard (garde jour/nuit, permanence, astreinte).",
            )

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
        return [IsAuthenticated()]

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
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        equipe = serializer.save()
        journaliser(self.request.user, "Ajout à l'équipe de rotation", cible=f"Equipe:{equipe.id}", details=f"{equipe.service.nom} - {equipe.agent.nom_complet} (ordre {equipe.ordre})")

    def perform_update(self, serializer):
        equipe = serializer.save()
        journaliser(self.request.user, "Modification de l'ordre de rotation", cible=f"Equipe:{equipe.id}", details=f"{equipe.service.nom} - {equipe.agent.nom_complet} (ordre {equipe.ordre})")

    def perform_destroy(self, instance):
        journaliser(self.request.user, "Retrait de l'équipe de rotation", cible=f"Equipe:{instance.id}", details=f"{instance.service.nom} - {instance.agent.nom_complet}")
        instance.delete()
