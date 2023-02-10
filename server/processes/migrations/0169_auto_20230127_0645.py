# Generated by Django 3.2.13 on 2023-01-27 06:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0168_runenvironment_aws_settings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='runenvironment',
            name='aws_ecs_default_platform_version',
            field=models.CharField(blank=True, choices=[('1.3.0', '1.3.0'), ('1.4.0', '1.4.0'), ('LATEST', 'LATEST')], default='', max_length=10),
        ),
        migrations.AlterField(
            model_name='task',
            name='aws_ecs_default_platform_version',
            field=models.CharField(blank=True, choices=[('1.3.0', '1.3.0'), ('1.4.0', '1.4.0'), ('LATEST', 'LATEST')], default='', max_length=10),
        ),
        migrations.AlterField(
            model_name='task',
            name='is_scheduling_managed',
            field=models.BooleanField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='is_service_managed',
            field=models.BooleanField(default=None, null=True),
        ),
    ]