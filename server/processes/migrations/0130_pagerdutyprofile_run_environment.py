# Generated by Django 2.2.14 on 2020-10-12 22:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0129_emailnotificationprofile_run_environment'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagerdutyprofile',
            name='run_environment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='processes.RunEnvironment'),
        ),
    ]
