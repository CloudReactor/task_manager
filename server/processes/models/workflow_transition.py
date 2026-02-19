from typing import Optional

import logging
import uuid

from django.db import models
from django.contrib.postgres.fields import ArrayField

from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)


class WorkflowTransition(models.Model):
    RULE_TYPE_ALWAYS = 'always'
    RULE_TYPE_ON_SUCCESS = 'success'
    RULE_TYPE_ON_FAILURE = 'failure'
    RULE_TYPE_ON_TIMEOUT = 'timeout'
    RULE_TYPE_ON_EXIT_CODE = 'exit_code'
    RULE_TYPE_THRESHOLD = 'threshold'
    RULE_TYPE_CUSTOM = 'custom'
    RULE_TYPE_DEFAULT = 'default'

    ALL_RULE_TYPES = [
        RULE_TYPE_ALWAYS,
        RULE_TYPE_ON_SUCCESS,
        RULE_TYPE_ON_FAILURE,
        RULE_TYPE_ON_TIMEOUT,
        RULE_TYPE_ON_EXIT_CODE,
        RULE_TYPE_THRESHOLD,
        RULE_TYPE_CUSTOM,
        RULE_TYPE_DEFAULT
    ]

    RULE_TYPE_CHOICES = [
        (x, x.replace('_', ' ').capitalize()) for x in ALL_RULE_TYPES
    ]

    THRESHOLD_PROPERTY_EXECUTION_TIME_SECONDS = 'execution_time'
    THRESHOLD_PROPERTY_SUCCESS_RATIO = 'success_ratio'
    THRESHOLD_PROPERTY_FAILURE_RATIO = 'failure_ratio'
    THRESHOLD_PROPERTY_SKIPPED_RATIO = 'skipped_ratio'

    ALL_THRESHOLD_PROPERTIES = [
        THRESHOLD_PROPERTY_EXECUTION_TIME_SECONDS,
        THRESHOLD_PROPERTY_SUCCESS_RATIO,
        THRESHOLD_PROPERTY_FAILURE_RATIO,
        THRESHOLD_PROPERTY_SKIPPED_RATIO
    ]

    THRESHOLD_PROPERTY_CHOICES = [
        (x, x.replace('_', '').capitalize()) for x in ALL_THRESHOLD_PROPERTIES
    ]

    THRESHOLD_COMPARATOR_EQUAL = '='
    THRESHOLD_COMPARATOR_NOT_EQUAL = '≠'
    THRESHOLD_COMPARATOR_LESS_THAN = '<'
    THRESHOLD_COMPARATOR_LESS_THAN_OR_EQUAL = '≤'
    THRESHOLD_COMPARATOR_GREATER_THAN = '>'
    THRESHOLD_COMPARATOR_GREATER_THAN_OR_EQUAL = '≥'

    ALL_THRESHOLD_COMPARATORS = [
        THRESHOLD_COMPARATOR_EQUAL,
        THRESHOLD_COMPARATOR_NOT_EQUAL,
        THRESHOLD_COMPARATOR_LESS_THAN,
        THRESHOLD_COMPARATOR_LESS_THAN_OR_EQUAL,
        THRESHOLD_COMPARATOR_GREATER_THAN,
        THRESHOLD_COMPARATOR_GREATER_THAN_OR_EQUAL
    ]

    THRESHOLD_COMPARATOR_CHOICES = [(x, x) for x in ALL_THRESHOLD_COMPARATORS]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    description = models.CharField(max_length=5000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    from_workflow_task_instance = models.ForeignKey(
        'WorkflowTaskInstance',
        # Don't backreference
        related_name='+',
        on_delete=models.CASCADE,
        db_column='from_workflow_process_type_instance_id')

    to_workflow_task_instance = models.ForeignKey(
        'WorkflowTaskInstance',
        # Don't backreference
        related_name='+',
        on_delete=models.CASCADE,
        db_column='to_workflow_process_type_instance_id')

    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    exit_codes = ArrayField(models.CharField(max_length=10), blank=True, null=True)
    threshold_property = models.CharField(max_length=50,
        choices=THRESHOLD_PROPERTY_CHOICES, blank=True)
    threshold_comparator = models.CharField(max_length=2,
        choices=THRESHOLD_COMPARATOR_CHOICES, blank=True)
    custom_expression = models.CharField(max_length=5000, blank=True)
    priority = models.PositiveIntegerField(blank=True, null=True)
    ui_color = models.CharField(max_length=16, blank=True)
    ui_line_style = models.CharField(max_length=50, blank=True)
    ui_scale = models.FloatField(null=True, blank=True)

    @property
    def workflow(self):
        wti = self.from_workflow_task_instance or \
                self.to_workflow_task_instance
        return wti.workflow

    def __str__(self) -> str:
        return (self.workflow.name or 'Unnamed') \
                + ' / ' + str(self.uuid)

    def should_activate_from(self, wtpie) -> bool:
        task_execution = wtpie.task_execution
        return self.should_activate(task_execution_status=task_execution.status,
                exit_code=task_execution.exit_code)

    def should_activate(self, task_execution_status, exit_code: Optional[int]) -> bool:
        from .execution import Execution

        pes = task_execution_status
        rt = self.rule_type

        if rt == self.RULE_TYPE_ALWAYS:
            return True
        elif rt == self.RULE_TYPE_ON_SUCCESS:
            return pes == Execution.Status.SUCCEEDED
        elif rt == self.RULE_TYPE_ON_FAILURE:
            return pes == Execution.Status.FAILED
        elif rt == self.RULE_TYPE_ON_TIMEOUT:
            return pes == Execution.Status.TERMINATED_AFTER_TIME_OUT
        elif rt == self.RULE_TYPE_ON_EXIT_CODE:
            return (self.exit_codes is not None) and (exit_code in self.exit_codes)
        else:
            # TODO handle other rule types
            raise APIException(detail=f"Unsupported rule type: {rt}")
