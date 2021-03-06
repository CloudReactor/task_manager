# Generated by Django 2.2.2 on 2019-11-11 06:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0057_auto_20191110_0123'),
    ]

    operations = [
        migrations.AddField(
            model_name='alertmethod',
            name='notify_on_failure',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='alertmethod',
            name='notify_on_success',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='alertmethod',
            name='notify_on_timeout',
            field=models.BooleanField(default=True),
        ),
    ]
