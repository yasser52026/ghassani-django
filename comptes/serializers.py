from rest_framework import serializers

from .models import Utilisateur, Notification


class NotificationSerializer(serializers.ModelSerializer):
    agent_nom = serializers.CharField(source='agent_concerne.nom_complet', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'message', 'agent_nom', 'lue', 'date_creation']


class UtilisateurSerializer(serializers.ModelSerializer):
    nom_complet = serializers.ReadOnlyField()
    mot_de_passe = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'email', 'matricule', 'nom', 'prenom', 'nom_complet',
            'fonction', 'cin', 'telephone', 'rib', 'role', 'service',
            'statut', 'disponible', 'mot_de_passe',
        ]

    def create(self, validated_data):
        mot_de_passe = validated_data.pop('mot_de_passe', None)
        utilisateur = Utilisateur(**validated_data)
        utilisateur.set_password(mot_de_passe)
        utilisateur.save()
        return utilisateur

    def update(self, instance, validated_data):
        mot_de_passe = validated_data.pop('mot_de_passe', None)
        for champ, valeur in validated_data.items():
            setattr(instance, champ, valeur)
        if mot_de_passe:
            instance.set_password(mot_de_passe)
        instance.save()
        return instance


class InscriptionSerializer(serializers.ModelSerializer):
    mot_de_passe = serializers.CharField(write_only=True)

    class Meta:
        model = Utilisateur
        fields = ['email', 'matricule', 'nom', 'prenom', 'mot_de_passe']

    def create(self, validated_data):
        mot_de_passe = validated_data.pop('mot_de_passe')
        utilisateur = Utilisateur(
            **validated_data, role='consultation', statut='en_attente', is_active=False,
        )
        utilisateur.set_password(mot_de_passe)
        utilisateur.save()
        return utilisateur


class ProfilPersonnelSerializer(serializers.ModelSerializer):
    mot_de_passe = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Utilisateur
        fields = ['nom', 'prenom', 'email', 'telephone', 'rib', 'mot_de_passe']

    def update(self, instance, validated_data):
        mot_de_passe = validated_data.pop('mot_de_passe', None)
        for champ, valeur in validated_data.items():
            setattr(instance, champ, valeur)
        if mot_de_passe:
            instance.set_password(mot_de_passe)
        instance.save()
        return instance


class ValidationInscriptionSerializer(serializers.Serializer):
    role = serializers.CharField()
    service_id = serializers.IntegerField(required=False, allow_null=True)
