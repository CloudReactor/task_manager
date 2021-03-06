# Generated by Django 2.2.2 on 2019-11-12 10:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0059_auto_20191112_1021'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessExecutionAlert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('error_code', models.IntegerField(blank=True, null=True)),
                ('error_message', models.CharField(blank=True, max_length=50000)),
                ('pagerduty_event_dedup_key', models.CharField(blank=True, max_length=1000)),
                ('alert_method', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.AlertMethod')),
                ('process_execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.ProcessExecution')),
            ],
        ),
    ]
