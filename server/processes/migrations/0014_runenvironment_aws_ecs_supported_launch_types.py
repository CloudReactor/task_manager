# Generated by Django 2.2.2 on 2019-07-01 06:43

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0013_auto_20190701_0439'),
    ]

    operations = [
        migrations.AddField(
            model_name='runenvironment',
            name='aws_ecs_supported_launch_types',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), blank=True, null=True, size=None),
        ),
    ]
