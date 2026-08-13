import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comptes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=255)),
                ('lue', models.BooleanField(default=False)),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('agent_concerne', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications_le_concernant', to='comptes.utilisateur')),
                ('destinataire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='comptes.utilisateur')),
            ],
            options={
                'ordering': ['-date_creation'],
            },
        ),
    ]
