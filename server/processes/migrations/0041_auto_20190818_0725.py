# Generated by Django 2.2.2 on 2019-08-18 07:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0040_auto_20190818_0713'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='workflowprocesstypeinstance',
            unique_together={('name', 'workflow')},
        ),
    ]
