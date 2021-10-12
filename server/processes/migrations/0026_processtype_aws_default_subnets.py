# Generated by Django 2.2.2 on 2019-07-25 06:24

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0025_runenvironment_aws_default_subnets'),
    ]

    operations = [
        migrations.AddField(
            model_name='processtype',
            name='aws_default_subnets',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=1000), blank=True, null=True, size=None),
        ),
    ]
