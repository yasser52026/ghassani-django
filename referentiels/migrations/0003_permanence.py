from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('referentiels', '0002_equipe'),
    ]

    operations = [
        migrations.AddField(
            model_name='poste',
            name='type_activite',
            field=models.CharField(choices=[('garde', 'Garde'), ('permanence', 'Permanence')], default='garde', max_length=15),
        ),
        migrations.AddField(
            model_name='equipe',
            name='type_activite',
            field=models.CharField(choices=[('garde', 'Garde'), ('permanence', 'Permanence')], default='garde', max_length=15),
        ),
        migrations.AlterModelOptions(
            name='equipe',
            options={'ordering': ['type_activite', 'ordre']},
        ),
        migrations.AlterUniqueTogether(
            name='equipe',
            unique_together={('service', 'type_activite', 'agent')},
        ),
    ]
