# Generated by Django 2.2.2 on 2019-10-14 06:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0050_processtype_aws_ecs_service_arn'),
    ]

    operations = [
        migrations.AddField(
            model_name='runenvironment',
            name='aws_workflow_starter_lambda_arn',
            field=models.CharField(blank=True, max_length=1000),
        ),
    ]
