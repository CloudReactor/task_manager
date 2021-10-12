from django.contrib.auth.models import Group
from django.db import models


class GroupInfo(models.Model):
    group = models.OneToOneField(
        Group, null=True, blank=True, related_name='group_info',
        on_delete=models.CASCADE)

    api_credits_used_current_month = models.BigIntegerField(default=0,
            null=False)
    api_credits_used_previous_month = models.BigIntegerField(default=0,
            null=False)

    api_last_used_at = models.DateTimeField(null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.group.name if self.group else str(self.pk)
