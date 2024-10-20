from django.db import models

from .alert import Alert


class LegacyHeartbeatDetectionAlert(Alert):
    heartbeat_detection_event = models.ForeignKey('LegacyHeartbeatDetectionEvent',
                                                  on_delete=models.CASCADE)
    class Meta:
        db_table = 'processes_heartbeatdetectionalert'
