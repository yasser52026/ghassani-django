from collections import defaultdict
from django.db import transaction

from calendrier.models import CATEGORIE_OUVRABLE, CATEGORIE_VENDREDI, CATEGORIE_RAMADAN, CATEGORIE_WEEKEND_FERIE
from calendrier.moteur import categorie_du_jour, categorie_du_jour_permanence, heures_bareme
from absences.models import Absence
from decomptes.models import Decompte
from referentiels.models import Equipe, Poste, TYPE_PERMANENCE
from .models import AffectationGarde, Garde, EtatRotation

PLAFOND_MENSUEL_PERMANENCE = 120


def agent_est_absent(agent_id, une_date):
    return Absence.objects.filter(agent_id=agent_id, date_debut__lte=une_date, date_fin__gte=une_date).exists()


def calculer_decomptes_mensuels(planning, jours_weekend=(5, 6)):
    est_permanence = planning.type_activite == TYPE_PERMANENCE
    categoriser = categorie_du_jour_permanence if est_permanence else categorie_du_jour

    resultats = defaultdict(lambda: {
        CATEGORIE_OUVRABLE: 0.0, CATEGORIE_VENDREDI: 0.0,
        CATEGORIE_RAMADAN: 0.0, CATEGORIE_WEEKEND_FERIE: 0.0,
        "nuit": 0.0, "total": 0.0,
    })
    for garde in planning.gardes.select_related('poste').prefetch_related('affectations'):
        categorie = categoriser(garde.date, jours_weekend)
        type_vacation = garde.poste.type_vacation
        heures = heures_bareme(type_vacation, categorie, garde.date, type_activite=planning.type_activite)
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
            agent_id=agent_id, service_id=planning.service_id, type_activite=planning.type_activite,
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


def heures_permanence_affectees(agent_id, planning, jours_weekend=(5, 6), exclure_garde_id=None):
    """Total d'heures de permanence déjà affectées à cet agent pour ce planning
    (ce service, ce mois), utilisé pour faire respecter le plafond de 120h/mois."""
    total = 0.0
    qs = planning.gardes.select_related('poste').prefetch_related('affectations')
    if exclure_garde_id is not None:
        qs = qs.exclude(id=exclure_garde_id)
    for garde in qs:
        if not garde.affectations.filter(agent_id=agent_id).exists():
            continue
        categorie = categorie_du_jour_permanence(garde.date, jours_weekend)
        total += heures_bareme(garde.poste.type_vacation, categorie, garde.date, type_activite=TYPE_PERMANENCE)
    return total


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


@transaction.atomic
def generer_rotation(planning):
    """Pré-remplit les gardes vides du planning à partir de l'ordre de rotation
    de l'équipe du service, propre au type d'activité (garde ou permanence).
    Un même agent ne peut jamais être proposé deux fois le même jour (par ex. jour
    ET nuit) : chaque date garde la trace des agents déjà retenus, tous postes
    confondus pour ce planning. Ne touche jamais une garde déjà affectée."""
    equipe = list(
        Equipe.objects.filter(service=planning.service, type_activite=planning.type_activite)
        .order_by('ordre').values_list('agent_id', flat=True)
    )
    if not equipe:
        return {'nb_affectations': 0, 'message': "Aucune équipe n'est configurée pour ce type d'activité sur ce service."}

    postes = list(Poste.objects.filter(service=planning.service, type_activite=planning.type_activite))
    if not postes:
        return {'nb_affectations': 0, 'message': "Aucun poste n'est configuré pour ce type d'activité sur ce service."}

    est_permanence = planning.type_activite == TYPE_PERMANENCE

    etats = {p.id: EtatRotation.objects.get_or_create(poste=p)[0] for p in postes}
    curseurs = {p.id: etats[p.id].index_suivant for p in postes}

    deja_pris = defaultdict(set)
    for a in AffectationGarde.objects.filter(garde__planning=planning).select_related('garde'):
        deja_pris[a.garde.date].add(a.agent_id)

    heures_permanence_cumulees = {}
    if est_permanence:
        for agent_id in equipe:
            heures_permanence_cumulees[agent_id] = heures_permanence_affectees(agent_id, planning)

    gardes_par_poste = {
        p.id: {g.date: g for g in planning.gardes.filter(poste=p).prefetch_related('affectations')}
        for p in postes
    }
    toutes_dates = sorted({d for gardes in gardes_par_poste.values() for d in gardes.keys()})

    nb_total = 0
    agents_bloques = set()

    for une_date in toutes_dates:
        for poste in postes:
            garde = gardes_par_poste[poste.id].get(une_date)
            if not garde or garde.affectations.exists():
                continue

            effectif = poste.effectif_attendu
            cursor = curseurs[poste.id]
            heures_garde = None
            if est_permanence:
                heures_garde = heures_bareme(
                    poste.type_vacation, categorie_du_jour_permanence(une_date), une_date,
                    type_activite=TYPE_PERMANENCE,
                )

            retenus = []
            essais = 0
            i = cursor
            while len(retenus) < effectif and essais < len(equipe) * 2:
                agent_id = equipe[i % len(equipe)]
                deja_retenu = agent_id in retenus
                deja_ce_jour = agent_id in deja_pris[une_date]
                absent = not deja_retenu and not deja_ce_jour and agent_est_absent(agent_id, une_date)
                depasse_plafond = False
                if est_permanence and not deja_retenu and not deja_ce_jour and not absent:
                    if heures_permanence_cumulees.get(agent_id, 0.0) + heures_garde > PLAFOND_MENSUEL_PERMANENCE:
                        depasse_plafond = True
                        agents_bloques.add(agent_id)

                if not deja_retenu and not deja_ce_jour and not absent and not depasse_plafond:
                    retenus.append(agent_id)
                i += 1
                essais += 1

            for agent_id in retenus:
                AffectationGarde.objects.create(garde=garde, agent_id=agent_id)
                deja_pris[une_date].add(agent_id)
                if est_permanence:
                    heures_permanence_cumulees[agent_id] = heures_permanence_cumulees.get(agent_id, 0.0) + heures_garde
            nb_total += len(retenus)
            curseurs[poste.id] = (cursor + effectif) % len(equipe)

    for poste in postes:
        etats[poste.id].index_suivant = curseurs[poste.id]
        etats[poste.id].save()

    message = None
    if agents_bloques:
        message = f"{len(agents_bloques)} agent(s) non affecté(s) sur certaines gardes : plafond de {PLAFOND_MENSUEL_PERMANENCE}h de permanence/mois atteint."
    return {'nb_affectations': nb_total, 'message': message}
