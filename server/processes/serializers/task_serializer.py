from typing import (
    Any, Mapping,
    # Type, Union,
    cast
)

import copy
import logging

from rest_framework import serializers
from rest_framework.exceptions import (
    APIException, ErrorDetail, ValidationError
)

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

from drf_spectacular.utils import (
    extend_schema_field,
    # PolymorphicProxySerializer,
)

from ..common.request_helpers import (
    ensure_group_access_level,
    required_user_and_group_from_request
)

from ..execution_methods import *
from ..common.utils import coalesce, deepmerge
from ..models.run_environment import RunEnvironment
from ..models.task import Task
from ..models.task_link import TaskLink
from ..models.user_group_access_level import UserGroupAccessLevel

from .name_and_uuid_serializer import NameAndUuidSerializer
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)

from .serializer_helpers import SerializerHelpers
from .group_setting_serializer_mixin import GroupSettingSerializerMixin
from .task_execution_serializer import TaskExecutionSerializer
from .task_execution_serializer_constants import TASK_EXECUTION_CONFIGURATION_FIELDS
from .link_serializer import LinkSerializer

logger = logging.getLogger(__name__)


SUPPORTED_EXECUTION_METHODS = [
    AwsCodeBuildExecutionMethod,
    AwsEcsExecutionMethod,
    AwsLambdaExecutionMethod,
    UnknownExecutionMethod,
]

UPPER_METHOD_TYPE_TO_EXECUTION_METHOD_NAME = {
    getattr(method, 'NAME').upper() :
        getattr(method, 'NAME') for method in SUPPORTED_EXECUTION_METHODS
}


# TODO: validate size of other_metadata, allowed ECS launch types
class TaskSerializer(GroupSettingSerializerMixin,
        EmbeddedIdValidatingSerializerMixin,
        FlexFieldsSerializerMixin,
        serializers.HyperlinkedModelSerializer,
        SerializerHelpers):
    """
    A Task is a specification for a runnable job, including details on how to
    run the task and how often the task is supposed to run.
    """

    class Meta:
        model = Task
        fields = [
            'uuid', 'name', 'url', 'description', 'dashboard_url',
            'max_manual_start_delay_before_alert_seconds',
            'max_manual_start_delay_before_abandonment_seconds',
            'heartbeat_interval_seconds',
            'max_heartbeat_lateness_before_alert_seconds',
            'max_heartbeat_lateness_before_abandonment_seconds',
            'schedule', 'scheduled_instance_count',
            'is_service', 'service_instance_count',
            'min_service_instance_count',
            'max_concurrency',
            'max_age_seconds', 'default_max_retries',
            'max_postponed_failure_count', 'max_postponed_missing_execution_count',
            'max_postponed_timeout_count',
            'min_missing_execution_delay_seconds',
            'notification_event_severity_on_success',
            'notification_event_severity_on_failure',
            'notification_event_severity_on_missing_execution',
            'notification_event_severity_on_missing_heartbeat',
            'notification_event_severity_on_service_down',
            'postponed_failure_before_success_seconds',
            'postponed_missing_execution_before_start_seconds',
            'postponed_timeout_before_success_seconds',
            'required_success_count_to_clear_failure',
            'required_success_count_to_clear_timeout',
            'project_url', 'log_query', 'logs_url',
            'links',
            'run_environment',
            'execution_method_type',
            'execution_method_capability_details',
            'capabilities',
            'is_scheduling_managed', 'scheduling_provider_type',
            'scheduling_settings',
            'is_service_managed', 'service_provider_type', 'service_settings',
            'default_input_value', 'input_value_schema', 'output_value_schema',
            'notification_profiles',
            'other_metadata',
            'latest_task_execution',
            'created_by_user', 'created_by_group',
            'was_auto_created', 'passive', 'enabled',
            'created_at', 'updated_at',
        ] + TASK_EXECUTION_CONFIGURATION_FIELDS

        read_only_fields = [
            'url', 'uuid',
            'is_service', 'capabilities',
            'latest_task_execution', 'current_service_info',
            'dashboard_url', 'logs_url',
            'created_at', 'updated_at',
        ]

    latest_task_execution = serializers.SerializerMethodField(
            allow_null=True)

    url = serializers.HyperlinkedIdentityField(
            view_name='tasks-detail',
            lookup_field='uuid')

    capabilities = serializers.SerializerMethodField()

    notification_profiles = NameAndUuidSerializer(
            include_name=True,
            view_name='notification_profiles-detail',
            many=True, required=False)

    links = LinkSerializer(many=True, required=False)

    @extend_schema_field(TaskExecutionSerializer)
    def get_latest_task_execution(self, obj: Task):
        if obj.latest_task_execution is None:
            return None

        # Set the Task so we don't get N+1 queries looking back
        # Seems to slow down in ECS even though it stops N+1 queries
        obj.latest_task_execution.task = obj

        return TaskExecutionSerializer(instance=obj.latest_task_execution,
                context=self.context, required=False,
                omit='marked_done_by,killed_by').data

    def get_capabilities(self, task: Task) -> list[str]:
        if task.passive:
            return []

        return [c.name for c in task.execution_method().capabilities()]

    def validate(self, attrs: Mapping[str, Any]) -> Mapping[str, Any]:
        task: Task | None = None
        if self.instance:
            task = cast(Task, self.instance)

        passive = attrs.get('passive')
        if (passive is None) and task:
            passive = task.passive

        if passive is None:
            passive = False

        execution_method_type = attrs.get('execution_method_type')

        if not execution_method_type:
            execution_method_type = task.execution_method_type if task \
                else UnknownExecutionMethod.NAME

        if (not passive) and (execution_method_type == UnknownExecutionMethod.NAME):
            raise ValidationError({
                'passive': [ErrorDetail('Non-passive Tasks may not have an Unknown execution method',
                        code='invalid')]
            })

        return attrs

    def to_internal_value(self, data: dict[str, Any]) -> dict[str, Any]:
        body_task_links = data.pop('links', None)

        validated = super().to_internal_value(data)

        request = self.context.get('request')
        user, group = required_user_and_group_from_request(request)

        task: Task | None = cast(Task, self.instance)

        if task is None:
            name = data.get('name')
            if name:
                task = Task.objects.filter(name=name, created_by_group=group).first()

        logger.info(f"to_internal_value(): existing {task=}")

        validated['__existing_instance__'] = task

        run_environment = cast(RunEnvironment | None, validated.get('run_environment',
            task.run_environment if task else None))

        if run_environment is None:
            raise ValidationError({
                'run_environment': ErrorDetail('Run Environment is required', 'missing')
            })

        # Ensure the API key has Developer access to the Run Environment
        # of the Task that will be updated.
        if task and task.run_environment and (run_environment.pk != task.run_environment.pk):
            ensure_group_access_level(group=group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                run_environment=task.run_environment,
                request=request)

        # Not sure why is_service isn't in validated even when specified in the
        # request body, falling back to original request.
        is_service = validated.pop('is_service', data.get('is_service'))
        service_instance_count = validated.get('service_instance_count')
        min_service_instance_count = validated.get('min_service_instance_count')
        is_service_managed = validated.get('is_service_managed')

        schedule = validated.get('schedule')
        scheduled_instance_count = validated.get('scheduled_instance_count')
        is_scheduling_managed = validated.get('is_scheduling_managed')

        if (service_instance_count is not None) and (service_instance_count > 0):
            if is_service is False:
                raise serializers.ValidationError({
                    'service_instance_count': ['Must be 0 or null for non-services']
                })
            is_service = True

        if (min_service_instance_count is not None) and (min_service_instance_count > 0):
            if is_service is False:
                raise serializers.ValidationError({
                    'service_instance_count': ['Must be 0 or null for non-services']
                })
            is_service = True

        if is_service_managed:
            if is_service is False:
                raise serializers.ValidationError({
                    'is_service_managed': ['Must be null or false for non-services']
                })
            is_service = True

        if scheduled_instance_count is not None:
            if scheduled_instance_count > 0:
                if is_service:
                    raise serializers.ValidationError({
                        'scheduled_instance_count': ['Must be 0 or null for services']
                    })
                is_service = False

        if is_scheduling_managed:
            if is_service:
                raise serializers.ValidationError({
                    'is_scheduling_managed': ['Must be null or false for services']
                })

            is_service = False

        if task:
            if (is_service is None) and (schedule is None):
                is_service = task.is_service
                logger.info(f"is_service and schedule are both None, inferring {is_service=} from Task ...")

                if not is_service:
                    schedule = task.schedule
                    logger.info(f"schedule is None, inferring {schedule=} from Task ...")

            if is_service and (is_service_managed is None) and (task.is_service_managed is not None):
                is_service_managed = task.is_service_managed

            if schedule and (is_scheduling_managed is None) and (task.is_scheduling_managed is not None):
                is_scheduling_managed = task.is_scheduling_managed

        schedule = schedule or ''
        is_service = is_service or False

        if is_service:
            # Possibly in the future allow Tasks to be both scheduled and services, but for now if schedule is set then is_service must be False
            if schedule:
                raise serializers.ValidationError({
                    'schedule': ['Must be blank for services']
                })

            task_service_instance_count: int | None = None
            task_min_service_instance_count: int | None = None

            if task:
                task_service_instance_count = task.service_instance_count
                task_min_service_instance_count = task.min_service_instance_count

            if service_instance_count is None:
                service_instance_count = max(coalesce(task_service_instance_count, min_service_instance_count, 1), 1)
            elif service_instance_count < 0:
                raise serializers.ValidationError({
                    'service_instance_count': ['Must be greater than or equal to 0 for services']
                })

            if min_service_instance_count is None:
                min_service_instance_count = max(coalesce(task_min_service_instance_count, 0), 0)
            elif min_service_instance_count < 0:
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be greater than or equal to 0 for services']
                })

            if min_service_instance_count > service_instance_count:
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be less than or equal to service_instance_count']
                })
        else:
            if is_service_managed:
                raise serializers.ValidationError({
                    'is_service_managed': ['Must be null or false for non-services']
                })

            service_instance_count = None
            min_service_instance_count = None
            is_service_managed = None

        validated['service_instance_count'] = service_instance_count
        validated['min_service_instance_count'] = min_service_instance_count
        validated['is_service_managed'] = is_service_managed

        if schedule:
            task_scheduled_instance_count: int | None = None

            if task:
                task_scheduled_instance_count = task.scheduled_instance_count

            if scheduled_instance_count is None:
                scheduled_instance_count = max(coalesce(task_scheduled_instance_count, 1), 1)
            elif scheduled_instance_count < 0:
                raise serializers.ValidationError({
                    'scheduled_instance_count': ['Must be greater than or equal to 0 for scheduled Tasks']
                })
        else:
            if is_scheduling_managed:
                raise serializers.ValidationError({
                    'is_scheduling_managed': ['Must be null or false for unscheduled Tasks']
                })

            is_scheduling_managed = None
            scheduled_instance_count = None

        validated['schedule'] = schedule
        validated['scheduled_instance_count'] = scheduled_instance_count
        validated['is_scheduling_managed'] = is_scheduling_managed

        emcd = validated.get('execution_method_capability_details')

        logger.debug(f"{emcd=}")

        execution_method_type: str | None = None

        if task:
            execution_method_type = task.execution_method_type

        execution_method_type = validated.get('execution_method_type',
            execution_method_type)

        if execution_method_type:
            known_execution_method_type = UPPER_METHOD_TYPE_TO_EXECUTION_METHOD_NAME.get(
                execution_method_type.upper())

            if known_execution_method_type:
                execution_method_type = known_execution_method_type
            else:
                logger.warning(f"Unsupported execution method type: '{execution_method_type}")
        else:
            execution_method_type = UnknownExecutionMethod.NAME

        if execution_method_type is None:
            raise APIException("TaskSerializer.to_internal_value() execution_method_type is None?")

        logger.debug(f"{execution_method_type=}")

        validated['execution_method_type'] = execution_method_type

        # Task.passive is False by default, which isn't compatible with the
        # default execution method of Unknown. So set it to True if
        # execution_method_type is Unknown and passive was not explicitly
        # specified in the request body. Note that validated['passive'] is True
        # if not explicitly set in data, due to the default value.
        if (execution_method_type == UnknownExecutionMethod.NAME) and \
            (data.get('passive') is None):
            validated['passive'] = True

        infrastructure_type = validated.get('infrastructure_type')
        infrastructure_settings = validated.get('infrastructure_settings')

        if task:
            if (emcd is not None) and task.execution_method_capability_details and \
                (task.execution_method_type == execution_method_type):
                emcd = deepmerge(task.execution_method_capability_details.copy(), emcd, 
                        ignore_none=False)
                validated['execution_method_capability_details'] = emcd
                logger.info(f"to_internal_value(): {task.uuid}: Merged old {emcd=}")
            else:
                logger.info(f"to_internal_value(): {task.uuid}: skipping emcd merge")

            infrastructure_settings = validated.get('infrastructure_settings')
            if (infrastructure_settings is not None) and task.infrastructure_settings and \
                    ((not infrastructure_type) or (task.infrastructure_type == infrastructure_type)):
                infrastructure_settings = deepmerge(task.infrastructure_settings.copy(),
                                                    infrastructure_settings, ignore_none=False)
                validated['infrastructure_settings'] = infrastructure_settings
                logger.info(f"to_internal_value(): {task.uuid}: Merged old {infrastructure_settings=}")
            else:
                logger.info(f"to_internal_value(): {task.uuid}: skipping infra merge")

            scheduling_provider_type = validated.get('scheduling_provider_type')
            scheduling_settings = validated.get('scheduling_settings')
            if (scheduling_settings is not None) and task.scheduling_settings and \
                    ((not scheduling_provider_type) or (task.scheduling_provider_type == scheduling_provider_type)):
                scheduling_settings = deepmerge(task.scheduling_settings.copy(),
                                                scheduling_settings, ignore_none=False)
                validated['scheduling_settings'] = scheduling_settings
                logger.info(f"to_internal_value(): {task.uuid}: Merged old {scheduling_settings=}")
            else:
                logger.info(f"to_internal_value(): {task.uuid}: skipping scheduling settings merge")

            service_provider_type = validated.get('service_provider_type')
            service_settings = validated.get('service_settings')
            if (service_settings is not None) and task.service_settings and \
                    ((not service_provider_type) or (task.service_provider_type == service_provider_type)):
                service_settings = deepmerge(task.service_settings.copy(), service_settings,
                                             ignore_none=False)
                validated['service_settings'] = service_settings
                logger.info(f"to_internal_value(): {task.uuid}: Merged old {service_settings=}")
            else:
                logger.info(f"to_internal_value(): {task.uuid}: skipping service settings merge")
        else:
            logger.info("to_internal_value(): skipping all merging because Task does not exist")

        self.set_validated_notification_profiles(data=data, validated=validated,
                run_environment=run_environment)

        if body_task_links is not None:
            updated_task_links = []

            next_rank = 0

            for body_task_link in body_task_links:
                rank = body_task_link.get('rank', next_rank)
                next_rank = rank + 1

                task_link = TaskLink(
                    name=body_task_link['name'],
                    link_url_template=body_task_link['link_url_template'],
                    description=body_task_link.get('description', ''),
                    icon_url=body_task_link.get('icon_url', ''),
                    rank=rank,
                    created_by_user=user,
                    created_by_group=group
                )
                updated_task_links.append(task_link)

            validated['task_links'] = updated_task_links


        return validated

    def to_representation(self, instance: Task) -> Any:
        obj = super().to_representation(instance)
        obj['links'] = LinkSerializer(instance=instance.tasklink_set,
                many=True).data
        return obj

    def create(self, validated_data: dict[str, Any]) -> Task:
        return self.create_or_update(None, validated_data)

    def update(self, instance: Task, validated_data: dict[str, Any]) -> Task:
        return self.create_or_update(instance, validated_data)

    def create_or_update(self, instance: Task | None, validated_data: dict[str, Any]) -> Task:
        #print(f"request = {self.context['request']}")
        #print(f"validated data = {validated_data}")
        request = self.context['request']

        user, _group = required_user_and_group_from_request(request=request)

        instance = validated_data.pop('__existing_instance__', instance)
        defaults = validated_data

        logger.info(f"Task create_or_update(), {validated_data=}, {instance=}")

        defaults.pop('uuid', None)

        notification_profiles = defaults.pop('notification_profiles', None)

        task_links = validated_data.pop('task_links', None)

        task: Task | None = instance

        old_self: Task | None = None
        if task is None:
            task = Task(**validated_data)

            if instance is None:
                task.created_by_user = user
        else:
            old_self = copy.copy(task)
            old_self.id = None
            
            for attr, value in validated_data.items():
                setattr(task, attr, value)

        task.should_skip_synchronize_with_run_environment = True
        task.save()

        task.synchronize_with_run_environment(old_self=old_self, is_saving=True)
        task.should_skip_synchronize_with_run_environment = False

        if notification_profiles is not None:
            task.notification_profiles.set(notification_profiles)

        if task_links is not None:
            task.tasklink_set.all().delete()
            for task_link in task_links:
                task_link.task = task
                task_link.save()

        return task
