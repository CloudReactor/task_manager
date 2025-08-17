import pytest

from conftest import *


@pytest.mark.django_db
def test_basic_run_environment_serialization(user_factory, run_environment_factory):
    user = user_factory()
    group = user.groups.all()[0]
    run_environment = run_environment_factory(
        created_by_group=group,
        created_by_user=user)

    context = context_with_authenticated_request(
        user=user, group=group)
    data = RunEnvironmentSerializer(run_environment, context=context).data
    validate_serialized_run_environment(data, run_environment)
