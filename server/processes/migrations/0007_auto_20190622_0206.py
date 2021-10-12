# Generated by Django 2.2.2 on 2019-06-22 02:06

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0006_auto_20190620_0904'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processtype',
            name='aws_ecs_default_security_groups',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=1000), null=True, size=None),
        ),
        migrations.AlterField(
            model_name='processtype',
            name='aws_ecs_supported_launch_types',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), null=True, size=None),
        ),
    ]
