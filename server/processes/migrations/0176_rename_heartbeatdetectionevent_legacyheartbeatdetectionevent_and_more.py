# Generated by Django 4.2.11 on 2024-04-28 09:21

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0175_event"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="HeartbeatDetectionEvent",
            new_name="LegacyHeartbeatDetectionEvent",
        ),
        migrations.AlterModelTable(
            name="legacyheartbeatdetectionevent",
            table="processes_heartbeatdetectionevent",
        ),
    ]
