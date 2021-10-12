from django.db import models

from . import Alert


class DelayedProcessStartAlert(Alert):
    delayed_process_start_detection_event = models.ForeignKey(
        'DelayedProcessStartDetectionEvent', on_delete=models.CASCADE)
