from django.conf import settings
from django.db import models

from django.utils.translation import gettext_lazy as _

from .run_environment import RunEnvironment


class UserRunEnvironmentAccessLevel(models.Model):
    ACCESS_LEVEL_READ_ONLY = 50
    ACCESS_LEVEL_SUPPORT = 100
    ACCESS_LEVEL_DEVELOPER = 500
    ACCESS_LEVEL_ADMIN = 1000

    class Meta:
        unique_together = (('user', 'run_environment'),)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='run_environment_access_levels',
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )

    run_environment = models.ForeignKey(RunEnvironment, on_delete=models.CASCADE)
    access_level = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'URA: user={self.user.username}, run_env={self.run_environment.name}, access_level={self.access_level}'
