from typing import Type

import logging
import binascii
import os

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import Group

from rest_framework.exceptions import PermissionDenied

from .uuid_model import UuidModel
from .subscription import Subscription

logger = logging.getLogger(__name__)


class SaasToken(UuidModel):
    DEPLOYMENT_KEY_NAME = 'Deployer'
    DEPLOYMENT_KEY_DESCRIPTION = 'Used to deploy Tasks to CloudReactor'
    TASK_KEY_NAME = 'Tasks'
    TASK_KEY_DESCRIPTION = 'Used by Tasks to report status to CloudReactor'

    ERROR_CODE_TOKEN_LIMIT_EXCEEDED = 'api_key_limit_exceeded'

    name = models.CharField(max_length=200, blank=True, default='')
    description = models.CharField(max_length=5000, blank=True, default='')

    """
    API key, associated with a user and a group.
    """
    key = models.CharField(_("Key"), max_length=40, primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='auth_tokens',
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )

    group = models.ForeignKey(
        Group, related_name='auth_tokens',
        on_delete=models.CASCADE, verbose_name=_("Group")
    )

    run_environment = models.ForeignKey('RunEnvironment',
            on_delete=models.CASCADE, null=True, blank=True)

    access_level = models.IntegerField(default=1)
    enabled = models.BooleanField(default=True)

    # deprecated 2020-08-03
    created = models.DateTimeField(_("Created"), auto_now_add=True)

    class Meta:
        # Work around for a bug in Django:
        # https://code.djangoproject.com/ticket/19422
        #
        # Also see corresponding ticket:
        # https://github.com/encode/django-rest-framework/issues/705
        abstract = 'rest_framework.authtoken' not in settings.INSTALLED_APPS
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def generate_key(self) -> str:
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self) -> str:
        return self.key


@receiver(pre_save, sender=SaasToken)
def pre_save_saas_token(sender: Type[SaasToken], **kwargs) -> None:
    instance = kwargs['instance']
    logger.info(f"pre-save with saas_token {instance}, {instance._state.adding=}, {instance.group=}")

    # https://stackoverflow.com/questions/2037320/what-is-the-canonical-way-to-find-out-if-a-django-model-is-saved-to-db
    if not instance._state.adding:
        logger.info('Updating an existing SaasToken')
        return

    group = instance.group
    existing_token_count = SaasToken.objects.filter(group=group).count()

    usage_limits = Subscription.compute_usage_limits(group)

    max_api_keys = usage_limits.max_api_keys

    if (max_api_keys is not None) and (existing_token_count >= max_api_keys):
        raise PermissionDenied(code=SaasToken.ERROR_CODE_TOKEN_LIMIT_EXCEEDED,
                detail=f"The group {group.name} already has {existing_token_count} API keys, exceeded its limit")
