from processes.models import WorkflowExecution

import factory
from faker import Factory as FakerFactory

from .uuid_model_factory import UuidModelFactory
from .user_factory import UserFactory

faker = FakerFactory.create()


class ExecutionFactory(UuidModelFactory):
    class Meta:
        model = WorkflowExecution

    run_reason = 0
    stop_reason = None
    started_by = factory.SubFactory(UserFactory)
    failed_attempts = 0
    timed_out_attempts = 0

