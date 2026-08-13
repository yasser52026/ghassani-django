from django.db import models


class Absence(models.Model):
    agent = models.ForeignKey('comptes.Utilisateur', on_delete=models.CASCADE, related_name='absences')
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif = models.CharField(max_length=200, blank=True)