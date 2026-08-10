from rest_framework import serializers
from .models import Service, Poste


class PosteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Poste
        fields = ['id', 'service', 'type_vacation', 'heure_debut', 'heure_fin', 'effectif_attendu']


class ServiceSerializer(serializers.ModelSerializer):
    postes = PosteSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'nom', 'description', 'vacation_cumulee', 'postes']
