import uuid

from django.conf import settings
from django.db import models

import stringcase

class UuidModel(models.Model):
    class Meta:
        abstract = True

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return str(self.uuid)

    @property
    def dashboard_url(self) -> str:
        return settings.EXTERNAL_BASE_URL + self.dashboard_path \
                + '/' + str(self.uuid)

    @property
    def dashboard_path(self) -> str:
        return stringcase.snakecase(type(self).__name__) + 's'
