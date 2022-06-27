from django.contrib.postgres.fields import HStoreField

from django.db import models

class AwsTaggedEntity(models.Model):
    class Meta:
        abstract = True

    aws_tags = HStoreField(blank=True, null=True)
