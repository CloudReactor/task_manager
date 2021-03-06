# Generated by Django 2.2.12 on 2020-04-23 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0108_auto_20200423_0612'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processexecution',
            name='status_update_interval_seconds',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='processexecution',
            name='status_update_message_max_bytes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='processexecution',
            name='status_update_port',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
