from collections import defaultdict
from django.db import transaction

from calendrier.models import CATEGORIE_OUVRABLE, CATEGORIE_VENDREDI, CATEGORIE_RAMADAN, CATEGORIE_WEEKEND_FERIE
from calendrier.moteur import categorie_du_jour, heures_bareme
from absences.models import Absence
from decomptes.models import Decompte
from .models import AffectationGarde, Garde


def agent_est_absent(agent_id, une_date):
    return Absence.objects.filter(agent_id=agent_id, date_debut__lte=une_date, date_fin__gte=une_date).exists()


def calculer_decomptes_mensuels(planning, jours_weekend=(5, 6)):
    resultats = defaultdict(lambda: {
        CATEGORIE_OUVRABLE: 0.0, CATEGORIE_VENDREDI: 0.0,
        CATEGORIE_RAMADAN: 0.0, CATEGORIE_WEEKEND_FERIE: 0.0,
        "nuit": 0.0, "total": 0.0,
    })
    for garde in planning.gardes.select_related('poste').prefetch_related('affectations'):
        categorie = categorie_du_jour(garde.date, jours_weekend)
        type_vacation = garde.poste.type_vacation
        heures = heures_bareme(type_vacation, categorie, garde.date)
        for affectation in garde.affectations.all():
            agent_id = affectation.agent_id
            if agent_est_absent(agent_id, garde.date):
                continue
            if type_vacation == "nuit":
                resultats[agent_id]["nuit"] += heures
            else:
                resultats[agent_id][categorie] += heures
            resultats[agent_id]["total"] += heures
    return resultats


@transaction.atomic
def enregistrer_decomptes(planning, jours_weekend=(5, 6)):
    resultats = calculer_decomptes_mensuels(planning, jours_weekend)
    for agent_id, valeurs in resultats.items():
        decompte, _ = Decompte.objects.get_or_create(
            agent_id=agent_id, service_id=planning.service_id,
            annee=planning.annee, mois=planning.mois,
        )
        decompte.heures_ouvrable = valeurs[CATEGORIE_OUVRABLE]
        decompte.heures_vendredi = valeurs[CATEGORIE_VENDREDI]
        decompte.heures_ramadan = valeurs[CATEGORIE_RAMADAN]
        decompte.heures_weekend_ferie = valeurs[CATEGORIE_WEEKEND_FERIE]
        decompte.heures_nuit = valeurs["nuit"]
        decompte.total_heures = valeurs["total"]
        decompte.statut_validation = "prepare"
        decompte.save()
    return resultats


def controler_planning(planning):
    alertes = []
    for garde in planning.gardes.select_related('poste').prefetch_related('affectations'):
        nb = garde.affectations.count()
        attendu = garde.poste.effectif_attendu or 1
        if nb == 0:
            alertes.append({'type': 'garde_vide', 'gravite': 'erreur', 'message': f"Garde du {garde.date} ({garde.poste.type_vacation}) non couverte."})
        elif nb < attendu:
            alertes.append({'type': 'effectif_reduit', 'gravite': 'avertissement', 'message': f"Garde du {garde.date} : {nb}/{attendu} agent(s)."})

        vus = set()
        for a in garde.affectations.all():
            if a.agent_id in vus:
                alertes.append({'type': 'doublon_agent', 'gravite': 'erreur', 'message': f"Agent en double le {garde.date}."})
            vus.add(a.agent_id)

    for garde in planning.gardes.all():
        for affectation in garde.affectations.all():
            conflits = AffectationGarde.objects.filter(
                agent_id=affectation.agent_id, garde__date=garde.date,
            ).exclude(garde__planning_id=planning.id).exclude(garde__poste_id=garde.poste_id)
            if conflits.exists():
                alertes.append({'type': 'conflit_inter_services', 'gravite': 'avertissement', 'message': f"Agent affecté ailleurs le {garde.date}."})
    return alertes
