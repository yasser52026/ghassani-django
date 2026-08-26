from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from comptes.models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR, ROLE_CHEF_SERVICE
from comptes.permissions import role_requis, acces_service_autorise
from .models import Decompte, JournalAudit, journaliser
from .serializers import DecompteSerializer, JournalAuditSerializer
from .exports import exporter_decomptes_excel, exporter_decomptes_pdf, exporter_trimestre_excel, exporter_trimestre_pdf
from referentiels.models import Service, TYPE_GARDE, TYPES_ACTIVITE

TYPES_VALIDES = {cle for cle, _ in TYPES_ACTIVITE}
TRIMESTRES = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}


def _type_activite_depuis_requete(request):
    valeur = request.query_params.get('type', TYPE_GARDE)
    return valeur if valeur in TYPES_VALIDES else TYPE_GARDE


def _decomptes_trimestre(service_id, annee, trimestre, type_activite):
    mois_liste = TRIMESTRES.get(int(trimestre))
    if not mois_liste:
        return None
    decomptes = Decompte.objects.filter(
        service_id=service_id, type_activite=type_activite, annee=annee, mois__in=mois_liste,
    ).select_related('agent')

    par_agent = {}
    for d in decomptes:
        if d.agent_id not in par_agent:
            par_agent[d.agent_id] = {
                'agent_matricule': d.agent.matricule, 'agent_nom': d.agent.nom_complet,
                'heures_ouvrable': 0.0, 'heures_weekend_ferie': 0.0, 'total_heures': 0.0,
            }
        entree = par_agent[d.agent_id]
        entree['heures_ouvrable'] += d.heures_ouvrable
        entree['heures_weekend_ferie'] += d.heures_weekend_ferie
        entree['total_heures'] += d.total_heures

    resultats = sorted(par_agent.values(), key=lambda x: -x['total_heures'])
    for r in resultats:
        r['total_heures'] = round(r['total_heures'], 2)
    return resultats


class DecompteMensuelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, mois):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        type_activite = _type_activite_depuis_requete(request)
        decomptes = Decompte.objects.filter(
            service_id=service_id, type_activite=type_activite, annee=annee, mois=mois
        ).select_related('agent').order_by('-total_heures')
        total = sum(d.total_heures for d in decomptes)
        return Response({'decomptes': DecompteSerializer(decomptes, many=True).data, 'total_general': total})


class DecompteTrimestrielView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, trimestre):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        type_activite = _type_activite_depuis_requete(request)
        resultats = _decomptes_trimestre(service_id, annee, trimestre, type_activite)
        if resultats is None:
            return Response({'detail': 'Trimestre invalide (1 à 4).'}, status=400)
        total_general = round(sum(r['total_heures'] for r in resultats), 2)
        return Response({'decomptes': resultats, 'total_general': total_general, 'mois': list(TRIMESTRES[int(trimestre)])})


class ExportTrimestreExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, trimestre):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        type_activite = _type_activite_depuis_requete(request)
        resultats = _decomptes_trimestre(service_id, annee, trimestre, type_activite)
        if resultats is None:
            return Response({'detail': 'Trimestre invalide (1 à 4).'}, status=400)
        service = Service.objects.get(id=service_id)
        fichier = exporter_trimestre_excel(service, annee, trimestre, resultats, type_activite)
        reponse = HttpResponse(fichier.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse['Content-Disposition'] = f'attachment; filename="{type_activite}_{service.nom}_T{trimestre}_{annee}.xlsx"'
        return reponse


class ExportTrimestrePdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, trimestre):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        type_activite = _type_activite_depuis_requete(request)
        resultats = _decomptes_trimestre(service_id, annee, trimestre, type_activite)
        if resultats is None:
            return Response({'detail': 'Trimestre invalide (1 à 4).'}, status=400)
        service = Service.objects.get(id=service_id)
        fichier = exporter_trimestre_pdf(service, annee, trimestre, resultats, type_activite)
        reponse = HttpResponse(fichier.read(), content_type="application/pdf")
        reponse['Content-Disposition'] = f'attachment; filename="bordereau_{type_activite}_{service.nom}_T{trimestre}_{annee}.pdf"'
        return reponse


class MesDecomptesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        decomptes = Decompte.objects.filter(agent=request.user).order_by('-annee', '-mois', 'type_activite')
        return Response(DecompteSerializer(decomptes, many=True).data)


class ExportExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, mois):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        type_activite = _type_activite_depuis_requete(request)
        service = Service.objects.get(id=service_id)
        decomptes = Decompte.objects.filter(
            service_id=service_id, type_activite=type_activite, annee=annee, mois=mois
        ).select_related('agent')
        fichier = exporter_decomptes_excel(service, annee, mois, decomptes, type_activite)
        reponse = HttpResponse(fichier.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse['Content-Disposition'] = f'attachment; filename="{type_activite}_{service.nom}_{annee}_{mois:02d}.xlsx"'
        return reponse


class ExportPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee, mois):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        type_activite = _type_activite_depuis_requete(request)
        service = Service.objects.get(id=service_id)
        decomptes = Decompte.objects.filter(
            service_id=service_id, type_activite=type_activite, annee=annee, mois=mois
        ).select_related('agent')
        fichier = exporter_decomptes_pdf(service, annee, mois, decomptes, type_activite)
        reponse = HttpResponse(fichier.read(), content_type="application/pdf")
        reponse['Content-Disposition'] = f'attachment; filename="bordereau_{type_activite}_{service.nom}_{annee}_{mois:02d}.pdf"'
        return reponse


class ValiderDecompteView(APIView):
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_CHEF_SERVICE, ROLE_DIRECTEUR)]

    def post(self, request, service_id, annee, mois):
        type_activite = _type_activite_depuis_requete(request)
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        decomptes = Decompte.objects.filter(service_id=service_id, type_activite=type_activite, annee=annee, mois=mois)
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
        journaliser(request.user, f"Validation de {nb} décompte(s)", cible=f"Service:{service_id} {mois}/{annee} [{type_activite}]")
        return Response({'nb_valides': nb})


class JournalAuditListView(APIView):
    """Journal d'audit paginé, avec filtre optionnel par date et par recherche libre."""
    permission_classes = [role_requis(ROLE_ADMIN, ROLE_DIRECTEUR)]
    TAILLE_PAGE = 60

    def get(self, request):
        entrees = JournalAudit.objects.all()

        date_filtre = request.query_params.get('date')
        if date_filtre:
            entrees = entrees.filter(horodatage__date=date_filtre)

        recherche = request.query_params.get('q', '').strip()
        if recherche:
            entrees = entrees.filter(
                Q(utilisateur_email__icontains=recherche) |
                Q(action__icontains=recherche) |
                Q(cible__icontains=recherche) |
                Q(details__icontains=recherche)
            )

        total = entrees.count()
        num_pages = max(1, (total + self.TAILLE_PAGE - 1) // self.TAILLE_PAGE)
        try:
            page = int(request.query_params.get('page', 1))
        except ValueError:
            page = 1
        page = max(1, min(page, num_pages))

        debut = (page - 1) * self.TAILLE_PAGE
        page_entrees = entrees[debut:debut + self.TAILLE_PAGE]

        return Response({
            'results': JournalAuditSerializer(page_entrees, many=True).data,
            'count': total,
            'page': page,
            'num_pages': num_pages,
            'page_size': self.TAILLE_PAGE,
        })


class TableauBordView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id, annee):
        if not acces_service_autorise(request.user, service_id):
            return Response(status=403)
        type_activite = _type_activite_depuis_requete(request)

        lignes = (
            Decompte.objects.filter(service_id=service_id, type_activite=type_activite, annee=annee)
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

        return Response({'annee': annee, 'mois': mois_data, 'type_activite': type_activite})
