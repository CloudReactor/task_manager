import uuid

from django.db import models

from .alert_method import AlertMethod
from .alert_send_status import AlertSendStatus


class Alert(models.Model):
    class Meta:
        abstract = True

    MAX_ERROR_MESSAGE_LENGTH = 50000
    MAX_SEND_RESULT_LENGTH = 50000

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    alert_method = models.ForeignKey(AlertMethod, on_delete=models.CASCADE)
    attempted_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    send_status = models.IntegerField(null=True, blank=True, default=AlertSendStatus.SENDING)
    send_result = models.CharField(max_length=MAX_SEND_RESULT_LENGTH, blank=True, default='')
    error_message = models.CharField(max_length=MAX_ERROR_MESSAGE_LENGTH, blank=True, default='')
