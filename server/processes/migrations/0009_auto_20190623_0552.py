# Generated by Django 2.2.2 on 2019-06-23 05:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('processes', '0008_saastoken'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='alertmethod',
            unique_together={('name', 'created_by_group')},
        ),
        migrations.AlterUniqueTogether(
            name='pagerdutyprofile',
            unique_together={('name', 'created_by_group')},
        ),
        migrations.AlterUniqueTogether(
            name='processtype',
            unique_together={('name', 'created_by_group')},
        ),
        migrations.AlterUniqueTogether(
            name='runenvironment',
            unique_together={('name', 'created_by_group')},
        ),
    ]
