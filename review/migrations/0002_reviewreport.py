# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('review', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(max_length=32, verbose_name='신고 사유')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='신고 일시')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_reports', to='users.user', verbose_name='신고자 아이디')),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='review.review', verbose_name='리뷰 아이디')),
            ],
            options={
                'db_table': 'reviewReports',
            },
        ),
        migrations.AddConstraint(
            model_name='reviewreport',
            constraint=models.UniqueConstraint(fields=('review', 'reporter'), name='unique_review_report_per_user'),
        ),
    ]
