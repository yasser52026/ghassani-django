from rest_framework import serializers
from .models import JourFerie, PeriodeRamadan, Bareme


class JourFerieSerializer(serializers.ModelSerializer):
    class Meta:
        model = JourFerie
        fields = ['id', 'date', 'libelle']


class PeriodeRamadanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodeRamadan
        fields = ['id', 'annee', 'date_debut', 'date_fin']


class BaremeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bareme
        fields = ['id', 'type_vacation', 'categorie_jour', 'heures', 'date_effet']
