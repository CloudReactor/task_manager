# Generated by Django 2.2.2 on 2019-06-30 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0011_auto_20190630_0746'),
    ]

    operations = [
        migrations.AddField(
            model_name='processtype',
            name='allocated_cpu_units',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='processtype',
            name='allocated_memory_mb',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
