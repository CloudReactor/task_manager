# Generated by Django 3.2.13 on 2022-09-14 23:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0164_auto_20220820_0851'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskexecution',
            name='execution_method_type',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
