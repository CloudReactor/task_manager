# Generated by Django 2.2.14 on 2020-08-07 05:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0011_update_proxy_permissions'),
        ('processes', '0115_auto_20200804_0135'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserRunEnvironmentAccessLevel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_level', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('run_environment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='processes.RunEnvironment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='run_environment_access_levels', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'unique_together': {('user', 'run_environment')},
            },
        ),
        migrations.CreateModel(
            name='UserGroupAccessLevel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_level', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Group')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_access_levels', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'unique_together': {('user', 'group')},
            },
        ),
    ]
