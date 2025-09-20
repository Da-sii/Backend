# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('review', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='updated',
            field=models.BooleanField(default=False, verbose_name='수정여부'),
        ),
    ]
