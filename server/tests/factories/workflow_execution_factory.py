from processes.models import WorkflowExecution

import factory
from faker import Factory as FakerFactory

from .workflow_factory import WorkflowFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class WorkflowExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkflowExecution

    workflow = factory.SubFactory(WorkflowFactory)
    status = WorkflowExecution.Status.RUNNING.value
    run_reason = 0
    stop_reason = None
    started_by = factory.SubFactory(UserFactory)
    failed_attempts = 0
    timed_out_attempts = 0
