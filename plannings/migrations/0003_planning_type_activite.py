from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plannings', '0002_etatrotation'),
    ]

    operations = [
        migrations.AddField(
            model_name='planning',
            name='type_activite',
            field=models.CharField(default='garde', max_length=15),
        ),
        migrations.AlterUniqueTogether(
            name='planning',
            unique_together={('service', 'type_activite', 'annee', 'mois')},
        ),
    ]
