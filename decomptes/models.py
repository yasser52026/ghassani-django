from django.db import models


class Decompte(models.Model):
    agent = models.ForeignKey('comptes.Utilisateur', on_delete=models.CASCADE, related_name='decomptes')
    service = models.ForeignKey('referentiels.Service', on_delete=models.CASCADE)
    type_activite = models.CharField(max_length=15, default='garde')
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
        unique_together = ('agent', 'annee', 'mois', 'service', 'type_activite')


class JournalAudit(models.Model):
    utilisateur_email = models.CharField(max_length=120, blank=True)
    action = models.CharField(max_length=255)
    cible = models.CharField(max_length=120, blank=True)
    details = models.TextField(blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-horodatage']


def journaliser(utilisateur, action, cible='', details=''):
    """Enregistre une entrée dans le journal d'audit (qui, quoi, quand)."""
    email = getattr(utilisateur, 'email', '') or ''
    JournalAudit.objects.create(
        utilisateur_email=email, action=action, cible=cible, details=details,
    )
