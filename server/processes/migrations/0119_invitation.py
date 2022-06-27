# Generated by Django 2.2.14 on 2020-08-09 21:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('processes', '0118_auto_20200809_2106'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invitation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('to_email', models.CharField(max_length=1000)),
                ('group_access_level', models.IntegerField()),
                ('confirmation_code', models.CharField(max_length=1000)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='auth.Group', verbose_name='Group')),
                ('invited_by_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_invitations', to=settings.AUTH_USER_MODEL, verbose_name='Invited by User')),
                ('invited_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming_invitations', to=settings.AUTH_USER_MODEL, verbose_name='Invited User')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
