from django.contrib import admin
from .models import Utilisateur, Notification

admin.site.register(Utilisateur)
admin.site.register(Notification)
