from rest_framework import serializers
from .models import Service, Poste, Equipe

class PosteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Poste
        fields = ['id', 'service', 'type_vacation', 'heure_debut', 'heure_fin', 'effectif_attendu']


class EquipeSerializer(serializers.ModelSerializer):
    agent_nom = serializers.CharField(source='agent.nom_complet', read_only=True)

    class Meta:
        model = Equipe
        fields = ['id', 'service', 'agent', 'agent_nom', 'ordre']


class ServiceSerializer(serializers.ModelSerializer):
    postes = PosteSerializer(many=True, read_only=True)
    equipe = EquipeSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'nom', 'description', 'vacation_cumulee', 'postes', 'equipe']