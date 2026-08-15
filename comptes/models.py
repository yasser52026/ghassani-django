from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

ROLE_ADMIN = "administrateur"
ROLE_GESTIONNAIRE = "gestionnaire"
ROLE_CHEF_SERVICE = "chef_service"
ROLE_DIRECTEUR = "directeur"
ROLE_CONSULTATION = "consultation"

ROLES = [
    (ROLE_ADMIN, "Administrateur"),
    (ROLE_GESTIONNAIRE, "Gestionnaire RH / Paie"),
    (ROLE_CHEF_SERVICE, "Chef de service"),
    (ROLE_DIRECTEUR, "Directeur"),
    (ROLE_CONSULTATION, "Consultation seule"),
]

FONCTION_MEDECIN = "medecin"
FONCTION_INFIRMIER = "infirmier"
FONCTION_AUTRE = "autre"

FONCTIONS = [
    (FONCTION_MEDECIN, "Médecin"),
    (FONCTION_INFIRMIER, "Infirmier"),
    (FONCTION_AUTRE, "Autre"),
]


class UtilisateurManager(BaseUserManager):
    def create_user(self, email, matricule, nom, prenom, password=None, **extra):
        if not email:
            raise ValueError("L'email est obligatoire")
        utilisateur = self.model(
            email=self.normalize_email(email), matricule=matricule,
            nom=nom, prenom=prenom, **extra,
        )
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, matricule, nom, prenom, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', ROLE_ADMIN)
        extra.setdefault('statut', 'actif')
        extra.setdefault('is_active', True)
        return self.create_user(email, matricule, nom, prenom, password, **extra)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    matricule = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)
    fonction = models.CharField(max_length=20, choices=FONCTIONS, blank=True, default=FONCTION_AUTRE)
    cin = models.CharField(max_length=20, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    rib = models.CharField(max_length=34, blank=True)
    role = models.CharField(max_length=30, choices=ROLES, default=ROLE_CONSULTATION)
    service = models.ForeignKey('referentiels.Service', null=True, blank=True, on_delete=models.SET_NULL, related_name='agents')
    statut = models.CharField(max_length=20, default='actif')
    disponible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['matricule', 'nom', 'prenom']

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def __str__(self):
        return f"{self.email} ({self.role})"


class Notification(models.Model):
    destinataire = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications')
    agent_concerne = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications_le_concernant')
    message = models.CharField(max_length=255)
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.destinataire} — {self.message}"
