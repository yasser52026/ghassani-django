from django.db import models

TYPE_GARDE = "garde"
TYPE_PERMANENCE = "permanence"
TYPES_ACTIVITE = [(TYPE_GARDE, "Garde"), (TYPE_PERMANENCE, "Permanence")]


class Service(models.Model):
    nom = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    vacation_cumulee = models.BooleanField(default=False)

    def __str__(self):
        return self.nom


class Poste(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='postes')
    type_activite = models.CharField(max_length=15, choices=TYPES_ACTIVITE, default=TYPE_GARDE)
    type_vacation = models.CharField(max_length=10)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    effectif_attendu = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.service.nom} - {self.type_activite} - {self.type_vacation}"


class Equipe(models.Model):
    """Ordre de rotation d'une équipe, défini une fois par service et par type d'activité
    (garde et permanence ont chacune leur propre équipe et leur propre ordre)."""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='equipe')
    type_activite = models.CharField(max_length=15, choices=TYPES_ACTIVITE, default=TYPE_GARDE)
    agent = models.ForeignKey('comptes.Utilisateur', on_delete=models.CASCADE)
    ordre = models.IntegerField()

    class Meta:
        unique_together = ('service', 'type_activite', 'agent')
        ordering = ['type_activite', 'ordre']

    def __str__(self):
        return f"{self.service.nom} [{self.type_activite}] #{self.ordre} - {self.agent.nom_complet}"
