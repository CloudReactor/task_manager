# Generated by Django 3.2.13 on 2022-06-12 04:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0161_auto_20220522_0516'),
    ]

    operations = [
        migrations.RenameField(
            model_name='task',
            old_name='execution_method_capability',
            new_name='execution_method_capability_details',
        ),
    ]
