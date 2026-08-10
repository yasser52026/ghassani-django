from django.http import HttpResponse
from django.db.models import Sum, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR, ROLE_CHEF_SERVICE
from comptes.permissions import role_requis, acces_service_autorise
from .models import Decompte, JournalAudit, journaliser
from .serializers import DecompteSerializer, JournalAuditSerializer
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
        journaliser(request.user, f"Validation de {nb} décompte(s)", cible=f"Service:{service_id} {mois}/{annee}")
        return Response({'nb_valides': nb})


class JournalAuditListView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_DIRECTEUR)]

    def get(self, request):
        entrees = JournalAudit.objects.all()[:200]
        return Response(JournalAuditSerializer(entrees, many=True).data)


class TableauBordView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)

        lignes = (
            Decompte.objects.filter(service_id=service_id, annee=annee)
            .values('mois')
            .annotate(
                total_heures=Sum('total_heures'),
                heures_nuit=Sum('heures_nuit'),
                heures_weekend_ferie=Sum('heures_weekend_ferie'),
                nb_agents=Count('agent', distinct=True),
            )
            .order_by('mois')
        )

        mois_data = []
        for ligne in lignes:
            nb_agents = ligne['nb_agents'] or 0
            total = ligne['total_heures'] or 0
            mois_data.append({
                'mois': ligne['mois'],
                'total_heures': round(total, 1),
                'nb_agents': nb_agents,
                'moyenne_agent': round(total / nb_agents, 1) if nb_agents else 0,
                'heures_nuit': round(ligne['heures_nuit'] or 0, 1),
                'heures_weekend_ferie': round(ligne['heures_weekend_ferie'] or 0, 1),
            })

        return Response({'annee': annee, 'mois': mois_data})
