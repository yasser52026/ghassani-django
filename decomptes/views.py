from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR, ROLE_CHEF_SERVICE
from comptes.permissions import role_requis, acces_service_autorise
from .models import Decompte, JournalAudit
from .serializers import DecompteSerializer
from .exports import exporter_decomptes_excel, exporter_decomptes_pdf
from referentiels.models import Service


class DecompteMensuelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, mois):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        decomptes = Decompte.objects.filter(service_id=service_id, annee=annee, mois=mois).select_related('agent').order_by('-total_heures')
        total = sum(d.total_heures for d in decomptes)
        return Response({'decomptes': DecompteSerializer(decomptes, many=True).data, 'total_general': total})


class MesDecomptesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        decomptes = Decompte.objects.filter(agent=request.user).order_by('-annee', '-mois')
        return Response(DecompteSerializer(decomptes, many=True).data)


class ExportExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, mois):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        service = Service.objects.get(id=service_id)
        decomptes = Decompte.objects.filter(service_id=service_id, annee=annee, mois=mois).select_related('agent')
        fichier = exporter_decomptes_excel(service, annee, mois, decomptes)
        reponse = HttpResponse(fichier.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse['Content-Disposition'] = f'attachment; filename="decompte_{service.nom}_{annee}_{mois:02d}.xlsx"'
        return reponse


class ExportPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, mois):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        service = Service.objects.get(id=service_id)
        decomptes = Decompte.objects.filter(service_id=service_id, annee=annee, mois=mois).select_related('agent')
        fichier = exporter_decomptes_pdf(service, annee, mois, decomptes)
        reponse = HttpResponse(fichier.read(), content_type="application/pdf")
        reponse['Content-Disposition'] = f'attachment; filename="bordereau_{service.nom}_{annee}_{mois:02d}.pdf"'
        return reponse


class ValiderDecompteView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_CHEF_SERVICE, ROLE_DIRECTEUR)]

    def post(self, request, service_id, annee, mois):
        decomptes = Decompte.objects.filter(service_id=service_id, annee=annee, mois=mois)
        nb = 0
        for d in decomptes:
            if request.user.role in (ROLE_CHEF_SERVICE, ROLE_ADMIN) and d.statut_validation == 'prepare':
                d.statut_validation = 'valide_chef'
                d.save()
                nb += 1
            elif request.user.role in (ROLE_DIRECTEUR, ROLE_ADMIN) and d.statut_validation == 'valide_chef':
                d.statut_validation = 'valide_directeur'
                d.save()
                nb += 1
        JournalAudit.objects.create(utilisateur_email=request.user.email, action=f"Validation de {nb} décompte(s)")
        return Response({'nb_valides': nb})
