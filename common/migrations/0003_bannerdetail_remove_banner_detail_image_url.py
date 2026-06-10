from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_banner_detail_image_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='BannerDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detail_image_url', models.URLField()),
                ('order', models.PositiveIntegerField(default=0)),
                ('banner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='details', to='common.banner')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.AlterModelOptions(
            name='banner',
            options={'ordering': ['order', 'id']},
        ),
        migrations.RemoveField(
            model_name='banner',
            name='detail_image_url',
        ),
    ]
