# Generated by Django 2.2.2 on 2020-03-25 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0097_processtype_aws_ecs_service_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processexecution',
            name='stop_reason',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
