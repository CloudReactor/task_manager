# Generated by Django 2.2.2 on 2020-02-04 23:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0088_auto_20200204_2332'),
    ]

    operations = [
        migrations.AddField(
            model_name='processtype',
            name='max_heartbeat_lateness_before_abandonment_seconds',
            field=models.IntegerField(blank=True, default=600, null=True),
        ),
    ]
