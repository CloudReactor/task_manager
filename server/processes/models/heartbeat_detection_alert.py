from django.db import models

from .alert import Alert


class HeartbeatDetectionAlert(Alert):
    heartbeat_detection_event = models.ForeignKey('HeartbeatDetectionEvent',
                                                  on_delete=models.CASCADE)
