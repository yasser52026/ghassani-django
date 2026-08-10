from datetime import date

from django.core.management.base import BaseCommand

from comptes.models import Utilisateur, ROLE_ADMIN
from calendrier.models import Bareme, CATEGORIE_OUVRABLE, CATEGORIE_VENDREDI, CATEGORIE_RAMADAN, CATEGORIE_WEEKEND_FERIE


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not Utilisateur.objects.filter(email="admin@chrfes.ma").exists():
            Utilisateur.objects.create_superuser(
                email="admin@chrfes.ma", matricule="ADMIN001",
                nom="Administrateur", prenom="Système", password="admin123",
            )
            self.stdout.write("Compte admin créé : admin@chrfes.ma / admin123")

        baremes = [
            ("jour", CATEGORIE_OUVRABLE, 4.5), ("jour", CATEGORIE_VENDREDI, 5.5),
            ("jour", CATEGORIE_RAMADAN, 6), ("jour", CATEGORIE_WEEKEND_FERIE, 12),
            ("nuit", CATEGORIE_OUVRABLE, 12), ("nuit", CATEGORIE_VENDREDI, 12),
            ("nuit", CATEGORIE_RAMADAN, 12), ("nuit", CATEGORIE_WEEKEND_FERIE, 12),
        ]
        for tv, cat, h in baremes:
            Bareme.objects.get_or_create(type_vacation=tv, categorie_jour=cat, date_effet=date(2026, 1, 1), defaults={'heures': h})
        self.stdout.write("Barème initialisé.")