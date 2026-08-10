import calendar
from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE
from comptes.permissions import role_requis, acces_service_autorise
from referentiels.models import Service, Poste
from calendrier.moteur import categorie_du_jour
from .models import Planning, Garde, AffectationGarde
from .services import enregistrer_decomptes, controler_planning

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _obtenir_ou_creer_planning(service, annee, mois):
    planning, _ = Planning.objects.get_or_create(service=service, annee=annee, mois=mois)
    nb_jours = calendar.monthrange(annee, mois)[1]
    postes = Poste.objects.filter(service=service)
    existantes = set(Garde.objects.filter(planning=planning).values_list('date', 'poste_id'))
    nouvelles = []
    for jour in range(1, nb_jours + 1):
        une_date = date(annee, mois, jour)
        for poste in postes:
            if (une_date, poste.id) not in existantes:
                nouvelles.append(Garde(planning=planning, poste=poste, date=une_date))
    if nouvelles:
        Garde.objects.bulk_create(nouvelles)
    return planning


class GrillePlanningView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, mois):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        service = Service.objects.get(id=service_id)
        planning = _obtenir_ou_creer_planning(service, annee, mois)

        nb_jours = calendar.monthrange(annee, mois)[1]
        postes = list(Poste.objects.filter(service=service).order_by('type_vacation'))
        gardes = list(planning.gardes.select_related('poste').prefetch_related('affectations__agent'))

        jours = []
        for jour in range(1, nb_jours + 1):
            une_date = date(annee, mois, jour)
            jours.append({
                'numero': jour, 'date': str(une_date),
                'nom_jour': ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"][une_date.weekday()],
                'categorie': categorie_du_jour(une_date),
            })

        gardes_data = []
        for g in gardes:
            gardes_data.append({
                'id': g.id, 'jour': g.date.day, 'poste_id': g.poste_id,
                'affectations': [{'id': a.id, 'agent_id': a.agent_id, 'agent_nom': a.agent.nom_complet} for a in g.affectations.all()],
            })

        agents = service.agents.filter(statut='actif').values('id', 'nom', 'prenom')
        agents_data = [{'id': a['id'], 'nom_complet': f"{a['prenom']} {a['nom']}"} for a in agents]

        return Response({
            'planning': {'id': planning.id, 'statut': planning.statut, 'annee': annee, 'mois': mois, 'mois_libelle': MOIS_FR[mois]},
            'postes': [{'id': p.id, 'type_vacation': p.type_vacation, 'heure_debut': str(p.heure_debut), 'heure_fin': str(p.heure_fin)} for p in postes],
            'jours': jours,
            'gardes': gardes_data,
            'agents_du_service': agents_data,
            'alertes': controler_planning(planning),
        })


class EnregistrerGrilleView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)]

    def post(self, request, planning_id):
        planning = Planning.objects.get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)

        affectations_par_garde = request.data.get('gardes', [])
        for entree in affectations_par_garde:
            garde_id = entree['garde_id']
            agent_ids = set(entree.get('agent_ids', []))
            actuels = set(AffectationGarde.objects.filter(garde_id=garde_id).values_list('agent_id', flat=True))

            AffectationGarde.objects.filter(garde_id=garde_id, agent_id__in=(actuels - agent_ids)).delete()
            for agent_id in (agent_ids - actuels):
                AffectationGarde.objects.create(garde_id=garde_id, agent_id=agent_id)

        return Response({'detail': 'Planning enregistré.'})


class CalculerView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)]

    def post(self, request, planning_id):
        planning = Planning.objects.get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)
        enregistrer_decomptes(planning)
        return Response({'detail': 'Décompte calculé.'})
