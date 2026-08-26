import calendar
from datetime import date

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE
from comptes.permissions import role_requis, acces_service_autorise
from referentiels.models import Service, Poste, TYPE_GARDE, TYPE_PERMANENCE, TYPE_ASTREINTE, TYPES_ACTIVITE
from calendrier.moteur import categorie_du_jour, categorie_du_jour_permanence, heures_bareme
from decomptes.models import journaliser
from .models import Planning, Garde, AffectationGarde
from .services import (
    enregistrer_decomptes, controler_planning,
    heures_permanence_affectees, unites_astreinte_affectees,
    PLAFOND_MENSUEL_PERMANENCE, PLAFOND_UNITES_ASTREINTE,
)
from .word_export import exporter_planning_word

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
JOURS_COURT = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
LIBELLES_TYPE = {TYPE_GARDE: "Garde", TYPE_PERMANENCE: "Permanence", TYPE_ASTREINTE: "Astreinte"}

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
        est_astreinte = type_activite == TYPE_ASTREINTE
        categoriser = categorie_du_jour_permanence if (est_permanence or est_astreinte) else categorie_du_jour

        nb_jours = calendar.monthrange(annee, mois)[1]
        postes = list(Poste.objects.filter(service=service, type_activite=type_activite).order_by('type_vacation'))
        gardes = list(planning.gardes.select_related('poste').prefetch_related('affectations__agent'))

        jours = []
        for jour in range(1, nb_jours + 1):
            une_date = date(annee, mois, jour)
            jours.append({
                'numero': jour, 'date': str(une_date),
                'nom_jour': JOURS_COURT[une_date.weekday()],
                'categorie': categoriser(une_date),
            })

        gardes_data = []
        for g in gardes:
            gardes_data.append({
                'id': g.id, 'jour': g.date.day, 'poste_id': g.poste_id,
                'affectations': [
                    {'id': a.id, 'agent_id': a.agent_id, 'agent_nom': a.agent.nom_complet, 'heures': a.heures}
                    for a in g.affectations.all()
                ],
            })

        agents_qs = service.agents.filter(statut='actif')
        if est_astreinte:
            agents_qs = agents_qs.filter(fonction='medecin')
        agents = agents_qs.values('id', 'nom', 'prenom')
        agents_data = [{'id': a['id'], 'nom_complet': f"{a['prenom']} {a['nom']}"} for a in agents]

        heures_permanence_par_agent = {}
        unites_astreinte_par_agent = {}
        if est_permanence:
            for a in agents_data:
                heures_permanence_par_agent[a['id']] = round(heures_permanence_affectees(a['id'], planning), 1)
        if est_astreinte:
            for a in agents_data:
                unites_astreinte_par_agent[a['id']] = unites_astreinte_affectees(a['id'], planning)

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
            'plafond_astreinte': PLAFOND_UNITES_ASTREINTE if est_astreinte else None,
            'unites_astreinte_par_agent': unites_astreinte_par_agent,
        })


class EnregistrerGrilleView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)]

    def post(self, request, planning_id):
        planning = Planning.objects.get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)

        est_permanence = planning.type_activite == TYPE_PERMANENCE
        est_astreinte = planning.type_activite == TYPE_ASTREINTE
        affectations_par_garde = request.data.get('gardes', [])
        nb_ajouts, nb_retraits = 0, 0

        if est_permanence:
            for entree in affectations_par_garde:
                garde_id = entree['garde_id']
                nouvelles = entree.get('affectations', [])
                nouveaux_ids = {int(n['agent_id']) for n in nouvelles}
                actuels_ids = set(AffectationGarde.objects.filter(garde_id=garde_id).values_list('agent_id', flat=True))

                a_retirer = actuels_ids - nouveaux_ids
                AffectationGarde.objects.filter(garde_id=garde_id, agent_id__in=a_retirer).delete()
                nb_retraits += len(a_retirer)

                for n in nouvelles:
                    agent_id = int(n['agent_id'])
                    heures = float(n.get('heures') or 0)
                    _, cree = AffectationGarde.objects.update_or_create(
                        garde_id=garde_id, agent_id=agent_id, defaults={'heures': heures},
                    )
                    if cree:
                        nb_ajouts += 1
        else:
            agents_valides = None
            if est_astreinte:
                agents_valides = set(planning.service.agents.filter(fonction='medecin').values_list('id', flat=True))

            for entree in affectations_par_garde:
                garde_id = entree['garde_id']
                agent_ids = set(entree.get('agent_ids', []))
                if agents_valides is not None:
                    agent_ids = {a for a in agent_ids if a in agents_valides}
                actuels = set(AffectationGarde.objects.filter(garde_id=garde_id).values_list('agent_id', flat=True))
                a_retirer = actuels - agent_ids
                a_ajouter = agent_ids - actuels
                AffectationGarde.objects.filter(garde_id=garde_id, agent_id__in=a_retirer).delete()
                for agent_id in a_ajouter:
                    AffectationGarde.objects.create(garde_id=garde_id, agent_id=agent_id)
                nb_ajouts += len(a_ajouter)
                nb_retraits += len(a_retirer)

        if nb_ajouts or nb_retraits:
            journaliser(
                request.user, "Modification du planning",
                cible=f"Planning:{planning.id}",
                details=f"{nb_ajouts} affectation(s) ajoutée(s), {nb_retraits} retirée(s).",
            )

        reponse = {'detail': 'Planning enregistré.'}
        if est_permanence:
            depassements = []
            for agent in planning.service.agents.filter(statut='actif'):
                total = heures_permanence_affectees(agent.id, planning)
                if total > PLAFOND_MENSUEL_PERMANENCE:
                    depassements.append({'agent_id': agent.id, 'agent_nom': agent.nom_complet, 'heures': round(total, 1)})
            if depassements:
                reponse['depassements'] = depassements
                noms = ", ".join(f"{d['agent_nom']} ({d['heures']} h)" for d in depassements)
                reponse['detail'] = (
                    f"Planning enregistré. Attention : {noms} dépasse(nt) {PLAFOND_MENSUEL_PERMANENCE} h — "
                    f"seules les 120 premières heures du mois seront comptées dans le décompte."
                )
        elif est_astreinte:
            depassements = []
            for agent in planning.service.agents.filter(statut='actif', fonction='medecin'):
                total = unites_astreinte_affectees(agent.id, planning)
                if total > PLAFOND_UNITES_ASTREINTE:
                    depassements.append({'agent_id': agent.id, 'agent_nom': agent.nom_complet, 'unites': total})
            if depassements:
                reponse['depassements'] = depassements
                noms = ", ".join(f"{d['agent_nom']} ({d['unites']} unités)" for d in depassements)
                reponse['detail'] = (
                    f"Planning enregistré. Attention : {noms} dépasse(nt) {PLAFOND_UNITES_ASTREINTE} unités — "
                    f"seules les {PLAFOND_UNITES_ASTREINTE} premières unités du mois seront comptées dans le décompte."
                )
        return Response(reponse)


class CalculerView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE)]

    def post(self, request, planning_id):
        planning = Planning.objects.get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)
        enregistrer_decomptes(planning)
        return Response({'detail': 'Décompte calculé.'})


class ExporterPlanningWordView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, planning_id):
        planning = Planning.objects.select_related('service').get(id=planning_id)
        if not acces_service_autorise(request.user, planning.service_id):
            return Response(status=403)

        est_permanence = planning.type_activite == TYPE_PERMANENCE
        postes = list(Poste.objects.filter(service=planning.service, type_activite=planning.type_activite).order_by('type_vacation'))
        postes_data = [{'id': p.id, 'type_vacation': p.type_vacation, 'heure_debut': str(p.heure_debut), 'heure_fin': str(p.heure_fin)} for p in postes]

        gardes = planning.gardes.select_related('poste').prefetch_related('affectations__agent')
        gardes_par_cle = {}
        for g in gardes:
            gardes_par_cle[f"{g.date.day}-{g.poste_id}"] = {
                'affectations': [{'agent_nom': a.agent.nom_complet, 'heures': a.heures} for a in g.affectations.all()],
            }

        nb_jours = calendar.monthrange(planning.annee, planning.mois)[1]
        jours = []
        for jour in range(1, nb_jours + 1):
            une_date = date(planning.annee, planning.mois, jour)
            jours.append({'numero': jour, 'nom_jour': JOURS_COURT[une_date.weekday()]})

        libelle_type = LIBELLES_TYPE.get(planning.type_activite, planning.type_activite)
        buffer = exporter_planning_word(planning, jours, postes_data, gardes_par_cle, libelle_type, planning.service.nom, est_permanence, planning.type_activite)

        reponse = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        nom_fichier = f"planning_{planning.type_activite}_{planning.service.nom}_{planning.annee}_{planning.mois:02d}.docx"
        reponse['Content-Disposition'] = f'attachment; filename="{nom_fichier}"'
        return reponse


class MesGardesView(APIView):
    """Gardes/permanences/astreintes de l'utilisateur connecté pour un mois donné."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        annee = int(request.query_params.get('annee', date.today().year))
        mois = int(request.query_params.get('mois', date.today().month))

        affectations = (
            AffectationGarde.objects.filter(agent=request.user, garde__date__year=annee, garde__date__month=mois)
            .select_related('garde__poste__service', 'garde__planning')
            .order_by('garde__date')
        )

        resultats = [{
            'date': str(a.garde.date),
            'jour_numero': a.garde.date.day,
            'jour_semaine': JOURS_FR[a.garde.date.weekday()],
            'service': a.garde.poste.service.nom,
            'type_activite': LIBELLES_TYPE.get(a.garde.planning.type_activite, a.garde.planning.type_activite),
            'type_activite_code': a.garde.planning.type_activite,
            'heures': a.heures,
            'heure_debut': str(a.garde.poste.heure_debut)[:5],
            'heure_fin': str(a.garde.poste.heure_fin)[:5],
        } for a in affectations]

        return Response({'annee': annee, 'mois': mois, 'mois_libelle': MOIS_FR[mois], 'gardes': resultats})
