# Generated by Django 2.2.14 on 2020-10-12 22:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0128_alertmethod_run_environment'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailnotificationprofile',
            name='run_environment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='processes.RunEnvironment'),
        ),
    ]
