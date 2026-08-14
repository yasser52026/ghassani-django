from django.db import models


class Planning(models.Model):
    service = models.ForeignKey('referentiels.Service', on_delete=models.CASCADE, related_name='plannings')
    type_activite = models.CharField(max_length=15, default='garde')
    annee = models.IntegerField()
    mois = models.IntegerField()
    statut = models.CharField(max_length=20, default='brouillon')

    class Meta:
        unique_together = ('service', 'type_activite', 'annee', 'mois')


class Garde(models.Model):
    planning = models.ForeignKey(Planning, on_delete=models.CASCADE, related_name='gardes')
    poste = models.ForeignKey('referentiels.Poste', on_delete=models.CASCADE)
    date = models.DateField()

    class Meta:
        unique_together = ('planning', 'poste', 'date')


class AffectationGarde(models.Model):
    garde = models.ForeignKey(Garde, on_delete=models.CASCADE, related_name='affectations')
    agent = models.ForeignKey('comptes.Utilisateur', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('garde', 'agent')


class EtatRotation(models.Model):
    """Mémorise où on en est dans le cycle de l'équipe pour un poste donné,
    pour que le mois suivant reprenne la rotation là où elle s'est arrêtée."""
    poste = models.OneToOneField('referentiels.Poste', on_delete=models.CASCADE, related_name='etat_rotation')
    index_suivant = models.IntegerField(default=0)
