import enum

@enum.unique
class NotificationSendStatus(enum.IntEnum):
    SENDING = 0
    SUCCEEDED = 1
    FAILED = 2
    TIMEOUT = 3
    RATE_LIMITED = 4
