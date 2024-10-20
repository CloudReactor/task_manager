import uuid

from django.db import models
from typedmodels.models import TypedModel

class Event(TypedModel):
    SEVERITY_CRITICAL = 600
    SEVERITY_ERROR = 500
    SEVERITY_WARNING = 400
    SEVERITY_INFO = 300
    SEVERITY_DEBUG = 200
    SEVERITY_TRACE = 100
    SEVERITY_NONE = 0

    # TODO: maybe use frozendict
    SEVERITY_TO_LABEL = {
        SEVERITY_CRITICAL: 'critical',
        SEVERITY_ERROR: 'error',
        SEVERITY_WARNING: 'warning',
        SEVERITY_INFO: 'info',
        SEVERITY_DEBUG: 'debug',
        SEVERITY_TRACE: 'trace',
        SEVERITY_NONE: 'none',
    }

    MAX_ERROR_SUMMARY_LENGTH = 200
    MAX_ERROR_DETAILS_MESSAGE_LENGTH = 50000
    MAX_SOURCE_LENGTH = 1000
    MAX_GROUPING_KEY_LENGTH = 5000

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event_at = models.DateTimeField(auto_now_add=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    severity = models.PositiveIntegerField(default=SEVERITY_ERROR)
    error_summary = models.CharField(max_length=MAX_ERROR_SUMMARY_LENGTH, blank=True)
    error_details_message = models.CharField(max_length=MAX_ERROR_DETAILS_MESSAGE_LENGTH, blank=True)
    source = models.CharField(max_length=MAX_SOURCE_LENGTH, blank=True)
    details = models.JSONField(null=True, blank=True)
    grouping_key = models.CharField(max_length=MAX_GROUPING_KEY_LENGTH, blank=True)
    resolved_at = models.DateTimeField(null=True)
    resolved_event = models.OneToOneField('self', on_delete=models.DO_NOTHING, null=True, blank=True)

    @property
    def severity_label(self):
        return self.SEVERITY_TO_LABEL.get(self.severity, 'unknown')

    def __repr__(self):
        return f"<{self.__class__.__name__}>, {self.error_summary}"
