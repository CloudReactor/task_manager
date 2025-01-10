from typing import Optional

import logging

from django.db import models
from django.contrib.auth.models import Group

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from ..exception import UnprocessableEntity

from .uuid_model import UuidModel
from .run_environment import RunEnvironment

logger = logging.getLogger(__name__)


class WorkflowTaskInstance(UuidModel):
    """
    A WorkflowTaskInstance contains a Task that is configured to run in
    a Workflow.
    """

    START_TRANSITION_CONDITION_ALL = 'all'
    START_TRANSITION_CONDITION_ANY = 'any'
    START_TRANSITION_CONDITION_COUNT_AT_LEAST = 'count_at_least'
    START_TRANSITION_CONDITION_RATIO_AT_LEAST = 'ratio_at_least'

    ALL_START_TRANSITION_CONDITIONS = [
        START_TRANSITION_CONDITION_ALL,
        START_TRANSITION_CONDITION_ANY,
        START_TRANSITION_CONDITION_COUNT_AT_LEAST,
        START_TRANSITION_CONDITION_RATIO_AT_LEAST,
    ]

    START_TRANSITION_CONDITION_CHOICES = [
        (x, x.replace('_', ' ').capitalize()) for x in ALL_START_TRANSITION_CONDITIONS
    ]

    FAILURE_BEHAVIOR_FAIL_WORKFLOW_ALWAYS = 'always_fail_workflow'
    FAILURE_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED = 'fail_workflow_if_unhandled'
    FAILURE_BEHAVIOR_IGNORE = 'ignore'

    ALL_FAILURE_BEHAVIORS = [
        FAILURE_BEHAVIOR_FAIL_WORKFLOW_ALWAYS,
        FAILURE_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED,
        FAILURE_BEHAVIOR_IGNORE,
    ]

    FAILURE_BEHAVIOR_CHOICES = [
        (x, x.replace('_', ' ').capitalize()) for x in ALL_FAILURE_BEHAVIORS
    ]

    TIMEOUT_BEHAVIOR_FAIL_WORKFLOW_ALWAYS = 'always_fail_workflow'
    TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_ALWAYS = 'always_timeout_workflow'
    TIMEOUT_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED = 'fail_workflow_if_unhandled'
    TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_IF_UNHANDLED = 'timeout_workflow_if_unhandled'
    TIMEOUT_BEHAVIOR_IGNORE = 'ignore'

    ALL_TIMEOUT_BEHAVIORS = [
        TIMEOUT_BEHAVIOR_FAIL_WORKFLOW_ALWAYS,
        TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_ALWAYS,
        TIMEOUT_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED,
        TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_IF_UNHANDLED,
        TIMEOUT_BEHAVIOR_IGNORE,
    ]

    TIMEOUT_BEHAVIOR_CHOICES = [
        (x, x.replace('_', ' ').capitalize()) for x in ALL_TIMEOUT_BEHAVIORS
    ]

    class Meta:
        db_table = 'processes_workflowprocesstypeinstance'
        ordering = ['name']
        unique_together = (('name', 'workflow'),)

    name = models.CharField(max_length=200)
    description = models.CharField(max_length=5000, blank=True)

    workflow = models.ForeignKey('Workflow',
            related_name='workflow_task_instances',
            on_delete=models.CASCADE)
    task = models.ForeignKey('Task', on_delete=models.CASCADE,
            db_column='process_type_id')
    start_transition_condition = models.CharField(max_length=20,
        choices=START_TRANSITION_CONDITION_CHOICES,
        default=START_TRANSITION_CONDITION_ALL)
    max_complete_executions = models.IntegerField(default=1, null=True, blank=True)
    should_eval_transitions_after_first_execution = models.BooleanField(default=False)
    condition_count_threshold = models.IntegerField(null=True, blank=True)
    condition_ratio_threshold = models.FloatField(null=True, blank=True)

    max_age_seconds = models.IntegerField(null=True, blank=True)
    default_max_retries = models.IntegerField(default=0)

    environment_variables_overrides = models.JSONField(null=True, blank=True)
    allocated_cpu_units = models.IntegerField(null=True, blank=True)
    allocated_memory_mb = models.IntegerField(null=True, blank=True)

    # Legacy
    use_task_alert_methods = models.BooleanField(default=False,
        db_column='use_process_type_alert_methods')

    use_task_notification_profiles = models.BooleanField(default=False)

    failure_behavior = models.CharField(max_length=50,
        choices=FAILURE_BEHAVIOR_CHOICES,
        default=FAILURE_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED)

    allow_workflow_execution_after_failure = models.BooleanField(default=False)

    timeout_behavior = models.CharField(max_length=50,
        choices=TIMEOUT_BEHAVIOR_CHOICES,
        default=TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_IF_UNHANDLED)

    allow_workflow_execution_after_timeout = models.BooleanField(default=False)

    ui_color = models.CharField(max_length=16, blank=True)
    ui_center_margin_top = models.FloatField(null=True, blank=True)
    ui_center_margin_left = models.FloatField(null=True, blank=True)
    ui_icon_type = models.CharField(max_length=50, blank=True)
    ui_scale = models.FloatField(null=True, blank=True)

    @classmethod
    def find_by_uuid_or_name(cls, obj_dict,
            required_group: Optional[Group] = None,
            required_run_environment: Optional[RunEnvironment] = None,
            check_conflict: bool = True):
        uuid = obj_dict.get('uuid')
        name = obj_dict.get('name')

        if uuid is not None:
            wti = cls.objects.get(uuid=uuid)

            if check_conflict and (name is not None) and (wti.name != name):
                raise UnprocessableEntity(
                        f"{cls.__name__} {uuid} is named '{wti.name}', not '{name}'")
        else:
            if name is None:
                raise serializers.ValidationError('Neither uuid or name found in request')

            wti = cls.objects.get(name=name)

        workflow = wti.workflow

        if required_group and (workflow.created_by_group != required_group):
            raise NotFound()

        if required_run_environment and (
                workflow.run_environment != required_run_environment):
            raise NotFound()

        return wti

    def __str__(self) -> str:
        return (self.name or 'Unnamed') + ' / ' + str(self.uuid)

    def start(self, workflow_execution):
        logger.info(f"Starting Workflow Task Instance with UUID = {self.uuid}, name = {self.name} ...")

        from .task_execution import TaskExecution
        from .workflow_task_instance_execution import WorkflowTaskInstanceExecution

        task_execution = TaskExecution(
          task=self.task,
          status=TaskExecution.Status.MANUALLY_STARTED,
        )

        logger.info(f"wti: new task execution emt = {task_execution.execution_method_type}")

        task_execution.save()

        logger.info(f"wti: save task execution emt = {task_execution.execution_method_type}")

        WorkflowTaskInstanceExecution.objects.filter(
            workflow_execution=workflow_execution,
            workflow_task_instance=self).update(is_latest=False)

        wtie = WorkflowTaskInstanceExecution(
            workflow_execution=workflow_execution,
            workflow_task_instance=self,
            task_execution=task_execution,
            is_latest=True
        )
        wtie.save()

        task_execution.manually_start()

        logger.info(f"Started Workflow Task Instance with UUID = {self.uuid}, name = {self.name}")

        return wtie

    def retry_if_unsuccessful(self, workflow_execution):
        latest_execution = self.find_latest_execution(workflow_execution)

        if latest_execution is None:
            logger.info(f"retry_if_unsuccessful() on wti {self.uuid} : no existing latest execution, starting ...")
            self.start(workflow_execution)
        else:
            task_execution = latest_execution.task_execution

            if task_execution.is_in_progress():
                logger.info(
                    f"retry_if_unsuccessful() on wti {self.uuid} : existing Task Execution {task_execution.uuid} in progress, not starting")
            elif task_execution.is_successful():
                logger.info(
                    f"retry_if_unsuccessful() on wti {self.uuid} : existing Task Execution {task_execution.uuid} was successful, transitioning out ...")
                workflow_execution.handle_workflow_task_instance_execution_finished(
                    latest_execution, retry_mode=True)
            else:
                logger.info(
                    f"retry_if_unsuccessful() on wti {self.uuid} : existing Task Execution {task_execution.uuid} was unsuccessful, starting ...")
                self.start(workflow_execution)

    def find_executions(self, workflow_execution):
        from .workflow_task_instance_execution import WorkflowTaskInstanceExecution

        return WorkflowTaskInstanceExecution.objects.filter(
            workflow_execution=workflow_execution, workflow_task_instance__uuid=self.uuid)

    def find_latest_executions(self, workflow_execution):
        return self.find_executions(workflow_execution).filter(is_latest=True)

    def find_latest_execution(self, workflow_execution):
        return self.find_latest_executions(workflow_execution).last()

    def find_activated_inbound_transition_evaluations(self, workflow_execution):
        from .workflow_transition import WorkflowTransition
        from .workflow_transition_evaluation import WorkflowTransitionEvaluation

        return WorkflowTransitionEvaluation.objects.filter(
            workflow_execution=workflow_execution, workflow_transition__uuid__in=
            WorkflowTransition.objects.filter(to_workflow_task_instance__uuid=self.uuid).
                values_list('uuid', flat=True),
            from_workflow_task_instance_execution__is_latest=True,
            result=True)

    def find_inbound_transitions(self):
        from .workflow_transition import WorkflowTransition
        return WorkflowTransition.objects.filter(to_workflow_task_instance=self)

    def handle_inbound_transition_activated(self,
        workflow_transition_evaluation, retry_mode=False):
        workflow_execution = workflow_transition_evaluation.workflow_execution

        completed_execution_count = self.find_latest_executions(workflow_execution).count()

        if (not self.should_eval_transitions_after_first_execution) and (not retry_mode) and \
                (completed_execution_count >= 1):
            logger.info(
                f"In workflow execution {workflow_execution.uuid}, skipping wti {self.uuid} since completed_execution_count {completed_execution_count} >= 1 and should_eval_transitions_after_first_execution == false and retry_mode = false")
            return False

        triggered = False

        if self.start_transition_condition == self.START_TRANSITION_CONDITION_ANY:
            triggered = True
        else:
            inbound_transition_evaluations = self.find_activated_inbound_transition_evaluations(workflow_execution)
            activated_transition_uuids = inbound_transition_evaluations.values_list('workflow_transition__uuid', flat=True)

            if self.start_transition_condition == self.START_TRANSITION_CONDITION_COUNT_AT_LEAST:
                if self.condition_count_threshold is None:
                    logger.warning(
                        "start_transition_condition == self.START_TRANSITION_CONDITION_COUNT_AT_LEAST but condition_count_threshold is not set, not activating")
                else:
                    triggered = len(activated_transition_uuids) >= self.condition_count_threshold
            else:
                all_transition_uuids = self.find_inbound_transitions().values_list('uuid', flat=True)
                if self.start_transition_condition == self.START_TRANSITION_CONDITION_ALL:
                    triggered = set(activated_transition_uuids) == set(all_transition_uuids)
                elif self.start_transition_condition == self.START_TRANSITION_CONDITION_RATIO_AT_LEAST:
                    if self.condition_ratio_threshold is None:
                        logger.warning(
                            "start_transition_condition == self.START_TRANSITION_CONDITION_RATIO_AT_LEAST but condition_ratio_threshold is not set, not activating")
                    else:
                        triggered = (len(activated_transition_uuids) / len(all_transition_uuids)) >= self.condition_ratio_threshold
                else:
                    raise Exception(f"Unknown start_transition_condition {self.start_transition_condition}")

        logger.info(f"For workflow execution {workflow_execution.uuid}, wti {self.uuid}, triggered = {triggered}")

        if not triggered:
            return False

        if retry_mode:
            logger.info(f"handle_inbound_transition_activated(): retrying wti {self.uuid} ...")
            self.retry_if_unsuccessful(workflow_execution)
            return True
        elif (self.max_complete_executions is None) or (completed_execution_count < self.max_complete_executions):
            logger.info(
                f"In workflow execution {workflow_execution.uuid}, starting wti {self.uuid}, completed_execution_count = {completed_execution_count}, max_complete_executions = {self.max_complete_executions}")
            logger.info(f"handle_inbound_transition_activated(): starting wti {self.uuid} ...")
            self.start(workflow_execution)
            return True
        else:
            logger.info(
                f"In workflow execution {workflow_execution.uuid}, not starting or retrying wti {self.uuid} since max execution count has been reached and should_eval_transitions_after_first_execution == False and retry_mode == False")
            return False
