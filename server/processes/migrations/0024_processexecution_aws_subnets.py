# Generated by Django 2.2.2 on 2019-07-25 06:09

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0023_auto_20190725_0523'),
    ]

    operations = [
        migrations.AddField(
            model_name='processexecution',
            name='aws_subnets',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=1000), null=True, size=None),
        ),
    ]
