import calendar
from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE
from comptes.permissions import role_requis, acces_service_autorise
from referentiels.models import Service, Poste, TYPE_GARDE, TYPE_PERMANENCE, TYPES_ACTIVITE
from calendrier.moteur import categorie_du_jour, categorie_du_jour_permanence, heures_bareme
from decomptes.models import journaliser
from .models import Planning, Garde, AffectationGarde
from .services import (
    enregistrer_decomptes, controler_planning, generer_rotation,
    heures_permanence_affectees, PLAFOND_MENSUEL_PERMANENCE,
)

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

TYPES_VALIDES = {cle for cle, _ in TYPES_ACTIVITE}


def _type_activite_depuis_requete(request):
    valeur = request.query_params.get('type', TYPE_GARDE)
    return valeur if valeur in TYPES_VALIDES else TYPE_GARDE


def _obtenir_ou_creer_planning(service, type_activite, annee, mois):
    planning, _ = Planning.objects.get_or_create(service=service, type_activite=type_activite, annee=annee, mois=mois)
    nb_jours = calendar.monthrange(annee, mois)[1]
    postes = Poste.objects.filter(service=service, type_activite=type_activite)
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
        type_activite = _type_activite_depuis_requete(request)
        service = Service.objects.get(id=service_id)
        planning = _obtenir_ou_creer_planning(service, type_activite, annee, mois)

        est_permanence = type_activite == TYPE_PERMANENCE
        categoriser = categorie_du_jour_permanence if est_permanence else categorie_du_jour

        nb_jours = calendar.monthrange(annee, mois)[1]
        postes = list(Poste.objects.filter(service=service, type_activite=type_activite).order_by('type_vacation'))
        gardes = list(planning.gardes.select_related('poste').prefetch_related('affectations__agent'))

        jours = []
        for jour in range(1, nb_jours + 1):
            une_date = date(annee, mois, jour)
            jours.append({
                'numero': jour, 'date': str(une_date),
                'nom_jour': ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"][une_date.weekday()],
                'categorie': categoriser(une_date),
            })

        gardes_data = []
        for g in gardes:
            gardes_data.append({
                'id': g.id, 'jour': g.date.day, 'poste_id': g.poste_id,
                'affectations': [{'id': a.id, 'agent_id': a.agent_id, 'agent_nom': a.agent.nom_complet} for a in g.affectations.all()],
            })

        agents = service.agents.filter(statut='actif').values('id', 'nom', 'prenom')
        agents_data = [{'id': a['id'], 'nom_complet': f"{a['prenom']} {a['nom']}"} for a in agents]

        heures_permanence_par_agent = {}
        if est_permanence:
            for a in agents_data:
                heures_permanence_par_agent[a['id']] = round(heures_permanence_affectees(a['id'], planning), 1)

        return Response({
            'planning': {
                'id': planning.id, 'statut': planning.statut, 'annee': annee, 'mois': mois,
                'mois_libelle': MOIS_FR[mois], 'type_activite': type_activite,
            },
            'postes': [{'id': p.id, 'type_vacation': p.type_vacation, 'heure_debut': str(p.heure_debut), 'heure_fin': str(p.heure_fin)} for p in postes],
            'jours': jours,
            'gardes': gardes_data,
            'agents_du_service': agents_data,
            'alertes': controler_planning(planning),
            'plafond_permanence': PLAFOND_MENSUEL_PERMANENCE if est_permanence else None,
            'heures_permanence_par_agent': heures_permanence_par_agent,
        })


class EnregistrerGrilleView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)]

    def post(self, request, planning_id):
        planning = Planning.objects.get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)

        est_permanence = planning.type_activite == TYPE_PERMANENCE
        affectations_par_garde = request.data.get('gardes', [])

        entrees = []
        for entree in affectations_par_garde:
            garde_id = entree['garde_id']
            agent_ids = set(entree.get('agent_ids', []))
            actuels = set(AffectationGarde.objects.filter(garde_id=garde_id).values_list('agent_id', flat=True))
            entrees.append({
                'garde_id': garde_id,
                'a_retirer': actuels - agent_ids,
                'a_ajouter': agent_ids - actuels,
            })

        agents_bloques = {}
        if est_permanence:
            gardes_par_id = {g.id: g for g in Garde.objects.filter(id__in=[e['garde_id'] for e in entrees]).select_related('poste')}
            heures_deja = {}
            heures_ajoutees = {}
            for e in entrees:
                garde = gardes_par_id.get(e['garde_id'])
                if not garde:
                    continue
                heures_garde = heures_bareme(
                    garde.poste.type_vacation, categorie_du_jour_permanence(garde.date), garde.date,
                    type_activite=TYPE_PERMANENCE,
                )
                for agent_id in e['a_ajouter']:
                    if agent_id not in heures_deja:
                        heures_deja[agent_id] = heures_permanence_affectees(agent_id, planning)
                    heures_ajoutees[agent_id] = heures_ajoutees.get(agent_id, 0.0) + heures_garde

            for agent_id, ajout in heures_ajoutees.items():
                if heures_deja.get(agent_id, 0.0) + ajout > PLAFOND_MENSUEL_PERMANENCE:
                    agents_bloques[agent_id] = round(heures_deja.get(agent_id, 0.0) + ajout, 1)

        nb_ajouts, nb_retraits = 0, 0
        for e in entrees:
            AffectationGarde.objects.filter(garde_id=e['garde_id'], agent_id__in=e['a_retirer']).delete()
            nb_retraits += len(e['a_retirer'])
            for agent_id in e['a_ajouter']:
                if agent_id in agents_bloques:
                    continue
                AffectationGarde.objects.create(garde_id=e['garde_id'], agent_id=agent_id)
                nb_ajouts += 1

        if nb_ajouts or nb_retraits:
            journaliser(
                request.user, "Modification du planning",
                cible=f"Planning:{planning.id}",
                details=f"{nb_ajouts} affectation(s) ajoutée(s), {nb_retraits} retirée(s).",
            )

        reponse = {'detail': 'Planning enregistré.'}
        if agents_bloques:
            reponse['agents_bloques'] = list(agents_bloques.keys())
            reponse['detail'] = (
                f"Planning enregistré, mais {len(agents_bloques)} agent(s) n'ont pas été affecté(s) : "
                f"plafond de {PLAFOND_MENSUEL_PERMANENCE}h de permanence/mois dépassé."
            )
        return Response(reponse)


class GenererRotationView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)]

    def post(self, request, planning_id):
        planning = Planning.objects.get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)

        resultat = generer_rotation(planning)
        journaliser(
            request.user, "Génération de la rotation",
            cible=f"Planning:{planning.id}",
            details=f"{resultat['nb_affectations']} affectation(s) proposée(s).",
        )
        return Response(resultat)


class CalculerView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)]

    def post(self, request, planning_id):
        planning = Planning.objects.get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)
        enregistrer_decomptes(planning)
        return Response({'detail': 'Décompte calculé.'})


JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
LIBELLES_TYPE = {TYPE_GARDE: "Garde", TYPE_PERMANENCE: "Permanence"}


class MesGardesView(APIView):
    """Liste des prochaines gardes/permanences de l'utilisateur connecté,
    destinée à un usage personnel (rôle consultation notamment)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import date, timedelta
        aujourdhui = date.today()
        limite = aujourdhui + timedelta(days=60)

        affectations = (
            AffectationGarde.objects.filter(agent=request.user, garde__date__gte=aujourdhui, garde__date__lte=limite)
            .select_related('garde__poste__service', 'garde__planning')
            .order_by('garde__date')
        )

        resultats = [{
            'date': str(a.garde.date),
            'jour_semaine': JOURS_FR[a.garde.date.weekday()],
            'service': a.garde.poste.service.nom,
            'type_activite': LIBELLES_TYPE.get(a.garde.planning.type_activite, a.garde.planning.type_activite),
            'type_vacation': 'Jour' if a.garde.poste.type_vacation == 'jour' else 'Nuit',
            'heure_debut': str(a.garde.poste.heure_debut)[:5],
            'heure_fin': str(a.garde.poste.heure_fin)[:5],
        } for a in affectations]

        return Response(resultats)
