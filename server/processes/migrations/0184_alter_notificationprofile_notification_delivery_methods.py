# Generated by Django 4.2.16 on 2024-11-24 11:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "processes",
            "0183_rename_insufficientserviceinstancesevent_legacyinsufficientserviceinstancesevent_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="notificationprofile",
            name="notification_delivery_methods",
            field=models.ManyToManyField(
                blank=True, to="processes.notificationdeliverymethod"
            ),
        ),
    ]