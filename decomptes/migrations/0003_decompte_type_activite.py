from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('decomptes', '0002_alter_journalaudit_options_journalaudit_cible_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='decompte',
            name='type_activite',
            field=models.CharField(default='garde', max_length=15),
        ),
        migrations.AlterUniqueTogether(
            name='decompte',
            unique_together={('agent', 'annee', 'mois', 'service', 'type_activite')},
        ),
    ]
