# Generated by Django 2.2.2 on 2020-03-22 05:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0096_auto_20200308_0325'),
    ]

    operations = [
        migrations.AddField(
            model_name='processtype',
            name='aws_ecs_service_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
