from django.utils import timezone

from processes.models import TaskExecution

import factory
from faker import Factory as FakerFactory

from .task_factory import TaskFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class TaskExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskExecution

    task = factory.SubFactory(TaskFactory)
    status = TaskExecution.Status.RUNNING.value
    run_reason = 0
    stop_reason = None
    started_by = factory.SubFactory(UserFactory)

    # Note: started_at has auto_add_now which is always set to the current time
    # on creation!

    failed_attempts = 0
    timed_out_attempts = 0
