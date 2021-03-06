# Generated by Django 2.2.2 on 2019-11-23 07:34

from django.db import migrations, models
import django.db.models.deletion
import processes.models.alert_send_status
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0068_auto_20191123_0723'),
    ]

    operations = [
        migrations.CreateModel(
            name='MissingScheduledProcessExecution',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('expected_execution_at', models.DateTimeField()),
                ('schedule', models.CharField(max_length=1000)),
                ('detected_at', models.DateTimeField(auto_now_add=True)),
                ('process_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.ProcessType')),
            ],
        ),
        migrations.CreateModel(
            name='MissingScheduledProcessExecutionAlert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('send_status', models.IntegerField(blank=True, default=processes.models.alert_send_status.AlertSendStatus(0), null=True)),
                ('send_result', models.CharField(blank=True, max_length=50000)),
                ('error_message', models.CharField(blank=True, max_length=50000)),
                ('alert_method', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.AlertMethod')),
                ('missing_scheduled_process_execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.MissingScheduledProcessExecution')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
