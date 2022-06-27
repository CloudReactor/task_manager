import logging

from urllib.parse import quote

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import Group

from templated_email import get_templated_mail

from .uuid_model import UuidModel

logger = logging.getLogger(__name__)


class Invitation(UuidModel):
    to_email = models.EmailField(max_length=1000)
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='incoming_invitations',
        on_delete=models.CASCADE,
        verbose_name=_('Invited User')
    )
    invited_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='outgoing_invitations',
        on_delete=models.CASCADE,
        verbose_name=_('Invited by User')
    )
    group = models.ForeignKey(
        Group,
        related_name='invitations',
        on_delete=models.CASCADE, verbose_name=_('Group')
    )
    group_access_level = models.IntegerField(null=True, blank=True)
    confirmation_code = models.CharField(max_length=1000)
    accepted_at = models.DateTimeField(null=True, blank=True)

    @property
    def acceptance_link(self) -> str:
        return settings.EXTERNAL_BASE_URL \
                + 'signup?invitation_code=' \
                + quote(self.confirmation_code)

    def send_email(self) -> None:
        template_params = {
            'invitation': self
        }

        email = get_templated_mail(
            template_name='invitation',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[self.to_email],
            context=template_params)

        email.reply_to = [settings.ENVIRON('DJANGO_EMAIL_REPLY_TO', default='no-reply@cloudreactor.io')]

        logger.info(f"Sending invitation email to {self.to_email} ...")
        email.send()
        logger.info(f"Done sending invitation email to {self.to_email}.")
