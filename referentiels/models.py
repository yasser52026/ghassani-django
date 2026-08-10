from django.db import models


class Service(models.Model):
    nom = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    vacation_cumulee = models.BooleanField(default=False)

    def __str__(self):
        return self.nom


class Poste(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='postes')
    type_vacation = models.CharField(max_length=10)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    effectif_attendu = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.service.nom} - {self.type_vacation}"
