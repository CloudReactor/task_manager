# Generated by Django 2.2.2 on 2019-07-25 05:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0022_auto_20190724_0718'),
    ]

    operations = [
        migrations.AddField(
            model_name='runenvironment',
            name='aws_access_key',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='runenvironment',
            name='aws_secret_key',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
