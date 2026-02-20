from django.db import models

from .task_event import TaskEvent

class InsufficientServiceTaskExecutionsEvent(TaskEvent):
    pass
