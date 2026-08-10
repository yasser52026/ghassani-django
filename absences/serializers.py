from rest_framework import serializers
from .models import Absence


class AbsenceSerializer(serializers.ModelSerializer):
    agent_nom = serializers.CharField(source='agent.nom_complet', read_only=True)

    class Meta:
        model = Absence
        fields = ['id', 'agent', 'agent_nom', 'date_debut', 'date_fin', 'motif']

    def validate(self, data):
        date_debut = data.get('date_debut', getattr(self.instance, 'date_debut', None))
        date_fin = data.get('date_fin', getattr(self.instance, 'date_fin', None))
        if date_debut and date_fin and date_fin < date_debut:
            raise serializers.ValidationError({'date_fin': "La date de fin ne peut pas être avant la date de début."})
        return data
