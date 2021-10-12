import enum

@enum.unique
class AlertSendStatus(enum.IntEnum):
    SENDING = 0
    SUCCEEDED = 1
    FAILED = 2
    TIMEOUT = 3
