# Generated by Django 3.2.6 on 2021-08-30 19:52

from django.db import migrations
from django.contrib.postgres.operations import CryptoExtension

class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0158_groupinfo'),
    ]

    operations = [
      CryptoExtension()
    ]
