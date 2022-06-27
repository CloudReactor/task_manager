# Generated by Django 2.2.2 on 2019-12-05 09:51

from django.db import migrations, models
import django.db.models.deletion
import processes.models.alert_send_status
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0074_auto_20191128_1920'),
    ]

    operations = [
        migrations.CreateModel(
            name='HeartbeatDetectionEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('detected_at', models.DateTimeField(auto_now_add=True)),
                ('last_heartbeat_at', models.DateTimeField(null=True)),
                ('expected_heartbeat_at', models.DateTimeField()),
                ('heartbeat_interval_seconds', models.IntegerField()),
                ('process_execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.ProcessExecution')),
                ('resolving', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='resolved_by', to='processes.HeartbeatDetectionEvent')),
            ],
            options={
                'ordering': ['detected_at'],
            },
        ),
        migrations.CreateModel(
            name='HeartbeatDetectionAlert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('send_status', models.IntegerField(blank=True, default=processes.models.alert_send_status.AlertSendStatus(0), null=True)),
                ('send_result', models.CharField(blank=True, max_length=50000)),
                ('error_message', models.CharField(blank=True, max_length=50000)),
                ('alert_method', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.AlertMethod')),
                ('heartbeat_detection_event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.HeartbeatDetectionEvent')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DelayedProcessStartDetectionEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('detected_at', models.DateTimeField(auto_now_add=True)),
                ('expected_started_before', models.DateTimeField(null=True)),
                ('process_execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.ProcessExecution')),
                ('resolving', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='resolved_by', to='processes.DelayedProcessStartDetectionEvent')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DelayedProcessStartAlert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('send_status', models.IntegerField(blank=True, default=processes.models.alert_send_status.AlertSendStatus(0), null=True)),
                ('send_result', models.CharField(blank=True, max_length=50000)),
                ('error_message', models.CharField(blank=True, max_length=50000)),
                ('alert_method', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.AlertMethod')),
                ('delayed_process_start_detection_event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.DelayedProcessStartDetectionEvent')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
