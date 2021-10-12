# Generated by Django 2.2.14 on 2020-08-09 21:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0117_set_group_admins'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usergroupaccesslevel',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_access_levels', to='auth.Group'),
        ),
    ]
