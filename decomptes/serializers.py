from rest_framework import serializers
from .models import Decompte


class DecompteSerializer(serializers.ModelSerializer):
    agent_matricule = serializers.CharField(source='agent.matricule', read_only=True)
    agent_nom = serializers.CharField(source='agent.nom_complet', read_only=True)

    class Meta:
        model = Decompte
        fields = [
            'id', 'agent', 'agent_matricule', 'agent_nom', 'service', 'annee', 'mois',
            'heures_ouvrable', 'heures_vendredi', 'heures_ramadan',
            'heures_weekend_ferie', 'heures_nuit', 'total_heures', 'statut_validation',
        ]
