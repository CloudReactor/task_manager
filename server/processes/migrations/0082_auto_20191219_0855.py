# Generated by Django 2.2.2 on 2019-12-19 08:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0081_auto_20191217_0709'),
    ]

    operations = [
        migrations.AddField(
            model_name='processtype',
            name='aws_ecs_default_assign_public_ip',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AddField(
            model_name='runenvironment',
            name='aws_ecs_default_assign_public_ip',
            field=models.BooleanField(default=False),
        ),
    ]
