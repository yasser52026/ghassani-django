from collections import defaultdict
from django.db import transaction

from calendrier.models import CATEGORIE_OUVRABLE, CATEGORIE_VENDREDI, CATEGORIE_RAMADAN, CATEGORIE_WEEKEND_FERIE
from calendrier.moteur import categorie_du_jour, categorie_du_jour_permanence, heures_bareme
from absences.models import Absence
from decomptes.models import Decompte
from referentiels.models import TYPE_PERMANENCE, TYPE_ASTREINTE
from .models import AffectationGarde

PLAFOND_MENSUEL_PERMANENCE = 120
PLAFOND_UNITES_ASTREINTE = 20
UNITE_ASTREINTE_HEURES_OUVRABLE = 16.5
UNITE_ASTREINTE_HEURES_FERIE = 24


def agent_est_absent(agent_id, une_date):
    return Absence.objects.filter(agent_id=agent_id, date_debut__lte=une_date, date_fin__gte=une_date).exists()


def calculer_unites_astreinte(nb_jours_ouvrable, nb_jours_ferie):
    """[(jours ouvrables x 16.5) + (jours fériés x 24)] / 16.5"""
    return (nb_jours_ouvrable * UNITE_ASTREINTE_HEURES_OUVRABLE + nb_jours_ferie * UNITE_ASTREINTE_HEURES_FERIE) / UNITE_ASTREINTE_HEURES_OUVRABLE


def calculer_decomptes_mensuels(planning, jours_weekend=(5, 6)):
    est_permanence = planning.type_activite == TYPE_PERMANENCE
    est_astreinte = planning.type_activite == TYPE_ASTREINTE
    categoriser = categorie_du_jour_permanence if (est_permanence or est_astreinte) else categorie_du_jour

    resultats = defaultdict(lambda: {
        CATEGORIE_OUVRABLE: 0.0, CATEGORIE_VENDREDI: 0.0,
        CATEGORIE_RAMADAN: 0.0, CATEGORIE_WEEKEND_FERIE: 0.0,
        "nuit": 0.0, "total": 0.0,
    })
    for garde in planning.gardes.select_related('poste').prefetch_related('affectations'):
        categorie = categoriser(garde.date, jours_weekend)
        type_vacation = garde.poste.type_vacation

        for affectation in garde.affectations.all():
            agent_id = affectation.agent_id
            if agent_est_absent(agent_id, garde.date):
                continue

            if est_astreinte:
                # Astreinte : on compte des JOURS (1 par affectation), pas des heures.
                resultats[agent_id][categorie] += 1
            elif est_permanence:
                # Permanence : pas de barème fixe, les heures sont saisies manuellement.
                heures = affectation.heures or 0.0
                resultats[agent_id][categorie] += heures
                resultats[agent_id]["total"] += heures
            else:
                heures = heures_bareme(type_vacation, categorie, garde.date, type_activite=planning.type_activite)
                if type_vacation == "nuit":
                    resultats[agent_id]["nuit"] += heures
                else:
                    resultats[agent_id][categorie] += heures
                resultats[agent_id]["total"] += heures

    if est_astreinte:
        for agent_id, valeurs in resultats.items():
            valeurs["total"] = calculer_unites_astreinte(valeurs[CATEGORIE_OUVRABLE], valeurs[CATEGORIE_WEEKEND_FERIE])

    return resultats


@transaction.atomic
def enregistrer_decomptes(planning, jours_weekend=(5, 6)):
    est_permanence = planning.type_activite == TYPE_PERMANENCE
    est_astreinte = planning.type_activite == TYPE_ASTREINTE
    resultats = calculer_decomptes_mensuels(planning, jours_weekend)
    for agent_id, valeurs in resultats.items():
        decompte, _ = Decompte.objects.get_or_create(
            agent_id=agent_id, service_id=planning.service_id, type_activite=planning.type_activite,
            annee=planning.annee, mois=planning.mois,
        )
        decompte.heures_ouvrable = valeurs[CATEGORIE_OUVRABLE]
        decompte.heures_vendredi = valeurs[CATEGORIE_VENDREDI]
        decompte.heures_ramadan = valeurs[CATEGORIE_RAMADAN]
        decompte.heures_weekend_ferie = valeurs[CATEGORIE_WEEKEND_FERIE]
        decompte.heures_nuit = valeurs["nuit"]

        total = valeurs["total"]
        if est_permanence:
            # Le service peut planifier au-delà de 120h, seules les 120 premières sont comptées.
            total = min(total, PLAFOND_MENSUEL_PERMANENCE)
        elif est_astreinte:
            # Idem pour l'astreinte : plafond de 20 unités par mois au niveau du décompte.
            total = min(total, PLAFOND_UNITES_ASTREINTE)
        decompte.total_heures = round(total, 2)
        decompte.statut_validation = "prepare"
        decompte.save()
    return resultats


def heures_permanence_affectees(agent_id, planning, exclure_garde_id=None):
    """Total brut (non plafonné) des heures de permanence déjà saisies pour cet agent."""
    qs = AffectationGarde.objects.filter(garde__planning=planning, agent_id=agent_id)
    if exclure_garde_id is not None:
        qs = qs.exclude(garde_id=exclure_garde_id)
    total = 0.0
    for a in qs:
        total += a.heures or 0.0
    return total


def unites_astreinte_affectees(agent_id, planning, jours_weekend=(5, 6)):
    """Unités d'astreinte brutes (non plafonnées) déjà planifiées pour cet agent ce mois."""
    nb_ouvrable, nb_ferie = 0, 0
    for garde in planning.gardes.all():
        if not garde.affectations.filter(agent_id=agent_id).exists():
            continue
        categorie = categorie_du_jour_permanence(garde.date, jours_weekend)
        if categorie == CATEGORIE_OUVRABLE:
            nb_ouvrable += 1
        else:
            nb_ferie += 1
    return round(calculer_unites_astreinte(nb_ouvrable, nb_ferie), 2)


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
