from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Utilisateur, ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR, ROLE_CHEF_SERVICE
from .serializers import UtilisateurSerializer, InscriptionSerializer, ValidationInscriptionSerializer
from .permissions import role_requis


class UtilisateurViewSet(viewsets.ModelViewSet):
    serializer_class = UtilisateurSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE)()]
        return [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR, ROLE_CHEF_SERVICE)()]

    def get_queryset(self):
        utilisateur = self.request.user
        base = Utilisateur.objects.exclude(statut='en_attente').order_by('nom')
        if utilisateur.role == ROLE_CHEF_SERVICE:
            return base.filter(service_id=utilisateur.service_id)
        return base


class MoiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)


class BasculerDisponibiliteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.disponible = not request.user.disponible
        request.user.save()
        return Response({'disponible': request.user.disponible})


class InscriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if Utilisateur.objects.filter(email=request.data.get('email', '').lower()).exists():
            return Response({'detail': "Cet email est déjà utilisé."}, status=status.HTTP_400_BAD_REQUEST)
        if Utilisateur.objects.filter(matricule=request.data.get('matricule')).exists():
            return Response({'detail': "Ce matricule existe déjà."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = InscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': "Demande envoyée, en attente de validation RH."}, status=status.HTTP_201_CREATED)


class EnAttenteListView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE)]

    def get(self, request):
        utilisateurs = Utilisateur.objects.filter(statut='en_attente').order_by('nom')
        return Response(UtilisateurSerializer(utilisateurs, many=True).data)


class ValiderInscriptionView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE)]

    def post(self, request, utilisateur_id):
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
        serializer = ValidationInscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur.role = serializer.validated_data['role']
        utilisateur.service_id = serializer.validated_data.get('service_id')
        utilisateur.statut = 'actif'
        utilisateur.is_active = True
        utilisateur.save()
        return Response({'detail': 'Compte activé.'})


class RejeterInscriptionView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_GESTIONNAIRE)]

    def post(self, request, utilisateur_id):
        Utilisateur.objects.filter(id=utilisateur_id).delete()
        return Response({'detail': 'Demande rejetée.'})
