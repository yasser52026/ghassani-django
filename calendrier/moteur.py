from .models import JourFerie, PeriodeRamadan, Bareme, CATEGORIE_OUVRABLE, CATEGORIE_VENDREDI, CATEGORIE_RAMADAN, CATEGORIE_WEEKEND_FERIE


def categorie_du_jour(une_date, jours_weekend=(5, 6)):
    est_ferie = JourFerie.objects.filter(date=une_date).exists()
    est_weekend = une_date.weekday() in jours_weekend

    if est_weekend or est_ferie:
        return CATEGORIE_WEEKEND_FERIE
    if une_date.weekday() == 4:
        return CATEGORIE_VENDREDI

    est_ramadan = PeriodeRamadan.objects.filter(
        date_debut__lte=une_date, date_fin__gte=une_date
    ).exists()
    return CATEGORIE_RAMADAN if est_ramadan else CATEGORIE_OUVRABLE


def categorie_du_jour_permanence(une_date, jours_weekend=(5, 6)):
    """La permanence ne distingue que jour ouvrable / jour férié (week-end ou jour
    férié) — contrairement à la garde, vendredi et ramadan comptent comme ouvrable."""
    est_ferie = JourFerie.objects.filter(date=une_date).exists()
    est_weekend = une_date.weekday() in jours_weekend
    return CATEGORIE_WEEKEND_FERIE if (est_weekend or est_ferie) else CATEGORIE_OUVRABLE


def heures_bareme(type_vacation, categorie_jour, a_la_date, type_activite="garde"):
    ligne = (
        Bareme.objects.filter(
            type_activite=type_activite, type_vacation=type_vacation,
            categorie_jour=categorie_jour, date_effet__lte=a_la_date,
        ).order_by('-date_effet').first()
    )
    return ligne.heures if ligne else 0.0
