from django.db import models


class Decompte(models.Model):
    agent = models.ForeignKey('comptes.Utilisateur', on_delete=models.CASCADE, related_name='decomptes')
    service = models.ForeignKey('referentiels.Service', on_delete=models.CASCADE)
    annee = models.IntegerField()
    mois = models.IntegerField()

    heures_ouvrable = models.FloatField(default=0)
    heures_vendredi = models.FloatField(default=0)
    heures_ramadan = models.FloatField(default=0)
    heures_weekend_ferie = models.FloatField(default=0)
    heures_nuit = models.FloatField(default=0)
    total_heures = models.FloatField(default=0)

    statut_validation = models.CharField(max_length=20, default='prepare')

    class Meta:
        unique_together = ('agent', 'annee', 'mois', 'service')


class JournalAudit(models.Model):
    utilisateur_email = models.CharField(max_length=120, blank=True)
    action = models.CharField(max_length=255)
    horodatage = models.DateTimeField(auto_now_add=True)
