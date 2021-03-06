# Generated by Django 2.2.14 on 2020-08-04 00:23

from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0112_auto_20200731_2110'),
    ]

    operations = [
        migrations.AddField(
            model_name='saastoken',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='saastoken',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='saastoken',
            name='uuid',
            field=models.UUIDField(editable=False, unique=True, null=True),
        ),
    ]
