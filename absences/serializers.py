from rest_framework import serializers
from .models import Absence


class AbsenceSerializer(serializers.ModelSerializer):
    agent_nom = serializers.CharField(source='agent.nom_complet', read_only=True)

    class Meta:
        model = Absence
        fields = ['id', 'agent', 'agent_nom', 'date_debut', 'date_fin', 'motif']
