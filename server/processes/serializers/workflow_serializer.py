#import ipdb
import logging

from typing import Optional, cast

from rest_framework import serializers
from rest_framework.exceptions import APIException, ErrorDetail, ValidationError

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

from ..exception.unprocessable_entity import UnprocessableEntity

from ..models import *
from .name_and_uuid_serializer import NameAndUuidSerializer
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)
from .group_setting_serializer_mixin import GroupSettingSerializerMixin
from .workflow_task_instance_serializer import WorkflowTaskInstanceSerializer
from .workflow_transition_serializer import WorkflowTransitionSerializer
from .workflow_execution_serializer import WorkflowExecutionSummarySerializer

logger = logging.getLogger(__name__)

COMMON_FIELDS = [
    'url', 'uuid', 'name', 'description', 'dashboard_url',
    'schedule', 'max_concurrency',
    'max_age_seconds', 'default_max_retries',
    'max_postponed_failure_count', 'max_postponed_missing_execution_count',
    'max_postponed_timeout_count',
    'min_missing_execution_delay_seconds',
    'notification_event_severity_on_success',
    'notification_event_severity_on_failure',
    'notification_event_severity_on_missing_execution',
    'notification_event_severity_on_missing_heartbeat',
    'notification_event_severity_on_service_down',
    'notification_event_severity_on_timeout',
    'postponed_failure_before_success_seconds',
    'postponed_missing_execution_before_start_seconds',
    'postponed_timeout_before_success_seconds',
    'required_success_count_to_clear_failure',
    'required_success_count_to_clear_timeout',
    'scheduled_instance_count',
    'latest_workflow_execution',
    'created_by_user', 'created_by_group',
    'run_environment',
    'enabled',
    'created_at', 'updated_at'
]

COMMON_READ_ONLY_FIELDS = [
    'url', 'uuid', 'dashboard_url',
    'latest_workflow_execution',
    'created_by_user', 'created_by_group',
    'created_at', 'updated_at'
]


class WorkflowSummarySerializer(GroupSettingSerializerMixin,
        serializers.HyperlinkedModelSerializer):
    """
    Selected properties of Workflows.
    """
    class Meta:
        model = Workflow
        fields = COMMON_FIELDS
        read_only_fields = COMMON_READ_ONLY_FIELDS

    latest_workflow_execution = WorkflowExecutionSummarySerializer(
            required=False, allow_null=True, read_only=True)
    url = serializers.HyperlinkedIdentityField(
            view_name='workflows-detail',
            lookup_field='uuid'
    )


class WorkflowSerializer(
        EmbeddedIdValidatingSerializerMixin,
        FlexFieldsSerializerMixin,
        WorkflowSummarySerializer):
    """
    Workflows are Tasks arranged in a directed graph. Configured Tasks
    are held by WorkflowTaskInstances, and WorkflowTransitions connect
    WorkflowTaskInstances together.
    """

    NEW_UUID_PREFIX = 'NEW_'

    class Meta:
        model = Workflow
        fields = COMMON_FIELDS + [
            'notification_profiles',
            'workflow_task_instances',
            'workflow_transitions',
        ]
        read_only_fields = COMMON_READ_ONLY_FIELDS

    workflow_task_instances = WorkflowTaskInstanceSerializer(
            many=True, read_only=True)

    workflow_transitions = WorkflowTransitionSerializer(many=True, read_only=True)

    notification_profiles = NameAndUuidSerializer(include_name=True,
            view_name='notification_profiles-detail', many=True, required=False)

    def to_internal_value(self, data):
        logger.info(f"wfs: to_internal value, data = {data}")

        workflow: Optional[Workflow] = cast(Workflow, self.instance) if self.instance else None

        data['description'] = data.get('description') or ''
        data['schedule'] = data.get('schedule') or ''
        data.pop('latest_workflow_execution', None)

        validated = super().to_internal_value(data)
        validated['workflow_task_instances'] = data.get('workflow_task_instances')
        validated['workflow_transitions'] = data.get('workflow_transitions')

        logger.debug(f"wfs: to_internal value, validated = {validated}")

        run_environment = validated.get('run_environment',
          workflow.run_environment if workflow else None)

        # Deprecated
        self.set_validated_alert_methods(data=data, validated=validated,
                run_environment=run_environment,
                allow_any_run_environment=(run_environment is None))

        self.set_validated_notification_profiles(data=data, validated=validated,
                run_environment=run_environment,
                allow_any_run_environment=(run_environment is None))

        return validated

    def create(self, validated_data):
        return self.create_or_update(None, validated_data)

    def update(self, instance, validated_data):
        return self.create_or_update(instance, validated_data)

    def create_or_update(self, instance, validated_data):
        defaults = validated_data

        # Deprecated
        alert_methods = defaults.pop('alert_methods', None)

        notification_profiles = defaults.pop('notification_profiles', None)
        wtis = defaults.pop('workflow_task_instances', None)
        wts = defaults.pop('workflow_transitions', None)

        if instance:
            super().update(instance, defaults)
            workflow = instance
        else:
            defaults.pop('uuid', None)
            workflow = Workflow(**defaults)
            workflow.save()

        # Legacy
        if alert_methods is not None:
            workflow.alert_methods.set(alert_methods)

        if notification_profiles is not None:
            workflow.notification_profiles.set(notification_profiles)

        if wtis is None:
            return workflow

        old_wtis_by_uuid = {}
        old_wtis_by_name = {}
        for wti in workflow.workflow_task_instances.select_related(
                'task__run_environment').all():
            old_wtis_by_uuid[str(wti.uuid)] = wti
            old_wtis_by_name[wti.name] = wti

        new_wtis_by_uuid = {}
        new_wtis_by_name = {}

        for wti_dict in wtis:
            wti_uuid = wti_dict.get('uuid')
            if wti_uuid:
                new_wtis_by_uuid[wti_uuid] = wti_dict
            else:
                wti_name = wti_dict.get('name')

                if wti_name is None:
                    raise ValidationError({
                        'workflow_task_instances': [
                            ErrorDetail('Workflow Task Instance missing uuid and name', code='invalid')
                        ]
                    })

                new_wtis_by_name[wti_name] = wti_dict

        for wti_uuid, wti in old_wtis_by_uuid.items():
            if (wti_uuid not in new_wtis_by_uuid) and (wti.name not in new_wtis_by_name):
                wti.delete()

        logger.info(f"old_wtis_by_uuid = {old_wtis_by_uuid}")

        old_wts_by_uuid = {}
        for wt in workflow.workflow_transitions().all():
            old_wts_by_uuid[str(wt.uuid)] = wt

        for wti_dict in wtis:
            wti_uuid = wti_dict.pop('uuid', None)
            wti_name = wti_dict.get('name')

            existing_wti = None

            if wti_uuid:
                if not wti_uuid.startswith(self.NEW_UUID_PREFIX):
                    existing_wti = old_wtis_by_uuid.get(wti_uuid)
                    if existing_wti is None:
                        raise ValidationError({
                            'workflow_task_instances': [
                                ErrorDetail(f'Workflow Task Instance with UUID {wti_uuid} is not part of Workflow',
                                        code='invalid')
                            ]
                        })

                    logger.info(f"Found existing WTI with UUID {wti_uuid}")
            elif wti_name:
                existing_wti = old_wtis_by_name.get(wti_name)
                if existing_wti is None:
                    raise ValidationError({
                        'workflow_task_instances': [
                            ErrorDetail(f"Workflow Task Instance with name '{wti_name}' is not part of Workflow",
                                    code='invalid')
                        ]
                    })

            ser = WorkflowTaskInstanceSerializer(instance=existing_wti, data=wti_dict,
                    partial=True, context=self.context, workflow=workflow,
                    for_embedded_deserialization=True)

            try:
                if not ser.is_valid():
                    msg = f"Error saving Workflow Task Instance with UUID {wti_uuid or '[Empty]'}, name '{wti_name or '[Empty]'}'"
                    logger.error(msg)

                    # ser.errors results in ValueError: Too many values to unpack
                    #errors = [error_detail.string for error_detail in ser.errors]

                    raise serializers.ValidationError({
                        'workflow_task_instances': [msg]
                    })
            except serializers.ValidationError as ve:
                logger.exception('workflow serializer validation error')
                raise serializers.ValidationError({
                    'workflow_task_instances': [str(ve)]
                }) from ve
            except UnprocessableEntity as ue:
                raise UnprocessableEntity({
                    'workflow_task_instances': [str(ue)]
                }) from ue
            except APIException as api_ex:
                raise APIException({
                    'workflow_task_instances': [str(api_ex)]
                }) from api_ex

            saved_wti = ser.save(workflow=workflow)
            if wti_uuid and wti_uuid.startswith(self.NEW_UUID_PREFIX):
                new_wtis_by_uuid[wti_uuid] = saved_wti

        if wts is None:
            # FIXME: handle case when transitions are not resent
            logger.info('Workflow Transitions not set')
        else:
            for wt_dict in wts:
                wt_uuid = wt_dict.pop('uuid', None)
                existing_wt = None

                if wt_uuid and not wt_uuid.startswith(self.NEW_UUID_PREFIX):
                    existing_wt = old_wts_by_uuid.pop(wt_uuid, None)

                    if existing_wt is None:
                        raise ValidationError({
                            'workflow_task_instances': [
                                ErrorDetail(f'Workflow Transition with UUID {wt_uuid} is not part of Workflow',
                                        code='invalid')
                            ]
                        })

                from_wti_dict = wt_dict.get('from_workflow_task_instance', None)
                if from_wti_dict:
                    wti_uuid = from_wti_dict['uuid']
                    if wti_uuid.startswith(self.NEW_UUID_PREFIX):
                        from_wti_dict['uuid'] = str(new_wtis_by_uuid[wti_uuid].uuid)

                to_wti_dict = wt_dict.get('to_workflow_task_instance', None)
                if to_wti_dict:
                    wti_uuid = to_wti_dict['uuid']
                    if wti_uuid.startswith(self.NEW_UUID_PREFIX):
                        to_wti_dict['uuid'] = str(new_wtis_by_uuid[wti_uuid].uuid)

                if existing_wt:
                    wts_ser = WorkflowTransitionSerializer(existing_wt, data=wt_dict, context=self.context)
                else:
                    wts_ser = WorkflowTransitionSerializer(data=wt_dict, context=self.context)

                wts_ser.is_valid(raise_exception=True)
                wts_ser.save()

            WorkflowTransition.objects.filter(uuid__in=old_wts_by_uuid.keys()).delete()

        return workflow
