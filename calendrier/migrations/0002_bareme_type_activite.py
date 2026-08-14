from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendrier', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bareme',
            name='type_activite',
            field=models.CharField(default='garde', max_length=15),
        ),
    ]
