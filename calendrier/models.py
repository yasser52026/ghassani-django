from django.db import models

CATEGORIE_OUVRABLE = "ouvrable"
CATEGORIE_VENDREDI = "vendredi"
CATEGORIE_RAMADAN = "ramadan"
CATEGORIE_WEEKEND_FERIE = "weekend_ferie"


class JourFerie(models.Model):
    date = models.DateField(unique=True)
    libelle = models.CharField(max_length=120)


class PeriodeRamadan(models.Model):
    annee = models.IntegerField()
    date_debut = models.DateField()
    date_fin = models.DateField()


class Bareme(models.Model):
    type_vacation = models.CharField(max_length=10)
    categorie_jour = models.CharField(max_length=20)
    heures = models.FloatField()
    date_effet = models.DateField()