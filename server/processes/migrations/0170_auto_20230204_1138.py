# Generated by Django 3.2.13 on 2023-02-04 11:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0169_auto_20230127_0645'),
    ]

    operations = [
        migrations.AddField(
            model_name='runenvironment',
            name='default_aws_lambda_configuration',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='runenvironment',
            name='aws_ecs_default_platform_version',
            field=models.CharField(blank=True, choices=[('1.3.0', '1.3.0'), ('1.4.0', '1.4.0'), ('LATEST', 'LATEST')], default='1.4.0', max_length=10),
        ),
        migrations.AlterField(
            model_name='task',
            name='aws_ecs_default_platform_version',
            field=models.CharField(blank=True, choices=[('1.3.0', '1.3.0'), ('1.4.0', '1.4.0'), ('LATEST', 'LATEST')], default='1.4.0', max_length=10),
        ),
    ]
