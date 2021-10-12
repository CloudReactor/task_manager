from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, null=True, blank=True, related_name='user_profile', on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username if self.user else str(self.pk)
