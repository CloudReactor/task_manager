from typing import Optional, Type

import enum
import logging

import networkx as nx

from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User

from django_middleware_global_request.middleware import get_request

from processes.common.notification import *
from processes.common.request_helpers import context_with_request
from processes.exception.unprocessable_entity import UnprocessableEntity

from .uuid_model import UuidModel
from .task_execution import TaskExecution
from .workflow import Workflow


logger = logging.getLogger(__name__)


class WorkflowExecution(UuidModel):
    """
    A WorkflowExecution holds data on a specific execution (run) of a Workflow.
    """

    @enum.unique
    class Status(enum.IntEnum):
        RUNNING = 0
        SUCCEEDED = 1
        FAILED = 2
        TERMINATED_AFTER_TIME_OUT = 3
        STOPPING = 6
        STOPPED = 7
        MANUALLY_STARTED = 8

    IN_PROGRESS_STATUSES = [
        Status.MANUALLY_STARTED,
        Status.RUNNING,
     ]

    COMPLETED_STATUSES = [
        Status.SUCCEEDED,
        Status.FAILED,
        Status.TERMINATED_AFTER_TIME_OUT,
        Status.STOPPING,
        Status.STOPPED,
    ]

    STATUSES_WITHOUT_MANUAL_INTERVENTION = [
        Status.MANUALLY_STARTED,
        Status.RUNNING,
        Status.SUCCEEDED,
        Status.FAILED
    ]

    @enum.unique
    class RunReason(enum.IntEnum):
        EXPLICIT_START = 0
        SCHEDULED_START = 1
        EXPLICIT_RETRY = 2

    @enum.unique
    class StopReason(enum.IntEnum):
        MANUAL = 0
        MAX_EXECUTION_TIME_EXCEEDED = 1

    FOUND_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE = \
        """Workflow '{{workflow.name}}' has started after being late according to its schedule"""

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    workflow_snapshot = models.JSONField(null=True, blank=True)
    status = models.IntegerField(default=Status.RUNNING.value)
    run_reason = models.IntegerField(default=0)
    stop_reason = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True, blank=True)
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   blank=True, related_name='+')
    finished_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    marked_done_at = models.DateTimeField(null=True, blank=True)
    marked_done_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                       blank=True, related_name='+')
    kill_started_at = models.DateTimeField(null=True, blank=True)
    kill_finished_at = models.DateTimeField(null=True, blank=True)
    kill_error_code = models.IntegerField(null=True, blank=True)
    killed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  blank=True, related_name='+')
    failed_attempts = models.IntegerField(default=0)
    timed_out_attempts = models.IntegerField(default=0)

    def __str__(self):
        return self.workflow.name + ' / ' + str(self.uuid)

    def workflow_task_instance_executions(self):
        from . import WorkflowTaskInstanceExecution
        return WorkflowTaskInstanceExecution.objects.prefetch_related('task_execution').\
            filter(workflow_execution=self).order_by('task_execution__started_at')

    def workflow_transition_evaluations(self):
        from . import WorkflowTransitionEvaluation
        return WorkflowTransitionEvaluation.objects.filter(
            workflow_execution=self).order_by('evaluated_at')

    def is_execution_continuation_allowed(self) -> bool:
        """
        Execution can continue as long as no manual intervention happened. A Workflow
        may fail (status = FAILED), but failure handlers may trigger another Task
        to run.
        """
        return self.status in WorkflowExecution.STATUSES_WITHOUT_MANUAL_INTERVENTION

    def manually_start(self) -> None:
        from processes.serializers import WorkflowSerializer

        logger.info(f"Manually starting workflow execution with UUID = {self.uuid} ...")

        if self.status != WorkflowExecution.Status.MANUALLY_STARTED:
            msg = f"Workflow execution has status {self.status}, can't manually start"
            logger.warning(msg)
            raise UnprocessableEntity(detail=msg)

        try:
            workflow = self.workflow

            request = get_request()

            self.workflow_snapshot = WorkflowSerializer(workflow,
                context=context_with_request()).data

            self.workflow_snapshot.pop('latest_workflow_execution')

            logger.info(f"Manually starting workflow with UUID = {workflow.uuid}, name = '{workflow.name}' ...")

            self.status = WorkflowExecution.Status.RUNNING
            # TODO: allows this to be SCHEDULED_START depending on parameter
            self.run_reason = WorkflowExecution.RunReason.EXPLICIT_START
            self.started_at = timezone.now()
            self.started_by = request.user
            self.save()

            roots = workflow.find_start_task_instances()

            for root in roots:
                logger.info(f"Starting root wpti uuid = {root.uuid}, name = {root.name}")
                root.start(workflow_execution=self)

            # In case there are no root processes
            self.check_if_complete()
        except Exception:
            logger.exception(f"Failed to start workflow {self.workflow.uuid}")
            self.status = WorkflowExecution.Status.FAILED
            self.finished_at = timezone.now()
            self.save()

    def retry(self):
        from . import WorkflowTaskInstanceExecution

        logger.info(f"Retrying workflow execution with UUID = {self.uuid} ...")

        self.invalidate_alerts()

        current_user: Optional[User] = None
        request = get_request()

        if request:
            current_user = request.user

        try:
            self.stop_running_task_executions(
                TaskExecution.StopReason.WORKFLOW_EXECUTION_RETRIED,
                current_user)

            now = timezone.now()

            wpti_uuids = WorkflowTaskInstanceExecution.objects.select_related('workflow_task_instance',
                'task_execution').filter(workflow_execution=self, is_latest=True).exclude(
                task_execution__status=TaskExecution.Status.SUCCEEDED).values_list(
                'workflow_task_instance__uuid', flat=True)

            self.invalidate_reachable_task_instance_executions(wpti_uuids)

            self.status = WorkflowExecution.Status.RUNNING
            self.run_reason = WorkflowExecution.RunReason.EXPLICIT_RETRY
            self.stop_reason = None
            self.started_at = now
            self.finished_at = None
            self.started_by = current_user

            roots = self.workflow.find_start_task_instances()

            for root in roots:
                logger.info(f"Retrying if unsuccessful root wpti uuid = {root.uuid}, name = {root.name}")
                root.retry_if_unsuccessful(workflow_execution=self)
        except Exception:
            logger.exception(f"Failed to retry workflow {self.workflow.uuid}")
            self.status = WorkflowExecution.Status.FAILED
            self.finished_at = timezone.now()
        finally:
            # In case there are no root processes
            self.check_if_complete()

        self.save()
        return self

    def handle_workflow_task_instance_execution_finished(self, wptie,
        skipped=False, retry_mode=False) -> None:
        from . import WorkflowTransitionEvaluation

        if self.status in [WorkflowExecution.Status.STOPPING, WorkflowExecution.Status.STOPPED]:
            logger.info(f"Ignoring task instance execution finished since workflow execution is already {self.status}")
            return

        try:
            # TODO: look this up differently if using the snapshot
            transitions = self.workflow.workflow_transitions().filter(
                from_workflow_task_instance=wptie.workflow_task_instance)

            logger.info(f"Found {len(transitions)} outbound transitions for wpti {wptie.workflow_task_instance.uuid}")

            activated_transitions = []

            for transition in transitions:
                if skipped:
                    # CHECKME: should we use the last Task Execution's properties?
                    should_activate = transition.should_activate(
                        task_execution_status=TaskExecution.Status.SUCCEEDED,
                        exit_code=0)
                else:
                    should_activate = transition.should_activate_from(wptie)

                logger.info(f"For workflow execution {self.uuid}, transition {transition.uuid}, should_activate = {should_activate}")

                wte = WorkflowTransitionEvaluation(result=should_activate,
                    workflow_execution=self,
                    from_workflow_task_instance_execution=wptie,
                    workflow_transition=transition)
                wte.save()

                if should_activate:
                    activated_transitions.append([transition, wte])

            self.check_if_complete(is_pending_transition_activation=len(activated_transitions) > 0)

            if self.status == TaskExecution.Status.RUNNING:
                first_ex = None
                for pair in activated_transitions:
                    transition = pair[0]
                    wte = pair[1]
                    try:
                        transition.to_workflow_task_instance.handle_inbound_transition_activated(
                            wte, retry_mode=retry_mode)
                    except Exception as ex:
                        logger.exception(f"Failed to activate wpti {transition.to_workflow_task_instance.uuid}")
                        first_ex = first_ex or ex

                if first_ex:
                    raise first_ex
        except Exception:
            logger.exception(f"Failed to execute workflow {self.workflow.uuid} after wpti {wptie.workflow_task_instance.uuid} finished")
            self.status = WorkflowExecution.Status.FAILED
            self.finished_at = timezone.now()
            self.save()

            self.send_alerts_if_necessary()
        finally:
            if self.status not in WorkflowExecution.IN_PROGRESS_STATUSES:
                # TODO
                pass

    def start_task_instance_executions(self, wti_uuids):
        from . import WorkflowTaskInstance

        wtis = WorkflowTaskInstance.objects.filter(uuid__in=wti_uuids,
                workflow=self.workflow)
        if wtis.count() < len(wti_uuids):
            raise UnprocessableEntity(
                  detail='Invalid workflow_task_instance UUID.')

        self.invalidate_alerts()

        self.status = WorkflowExecution.Status.RUNNING
        self.save()

        self.invalidate_reachable_task_instance_executions(wti_uuids)

        for wti in wtis:
            logger.info(f"Manually starting wti uuid = {wti.uuid}, name = {wti.name}")
            wti.start(workflow_execution=self)

        self.refresh_from_db()
        self.check_if_complete()
        return self

    def invalidate_reachable_task_instance_executions(self, wti_uuids) -> None:
        from . import WorkflowTaskInstanceExecution

        logger.info(f"wti UUIDs = {wti_uuids}")

        mdg, _uuid_to_wti, _uuid_to_wt = self.make_multidigraph_and_lookup_tables()

        reachable_wti_uuids = set()
        for wti_uuid in wti_uuids:
            reachable_wti_uuids |= set(nx.dfs_preorder_nodes(mdg, str(wti_uuid)))

        logger.info(f"Reachable wti UUIDs = {reachable_wti_uuids}")

        WorkflowTaskInstanceExecution.objects.select_related('workflow_task_instance').filter(
                workflow_task_instance__uuid__in=reachable_wti_uuids).update(is_latest=False)

    def check_if_complete(self, is_pending_transition_activation=False) -> bool:
        updated_status = self.compute_updated_status(is_pending_transition_activation)

        if updated_status != self.status:
            self.status = updated_status

            if updated_status not in WorkflowExecution.IN_PROGRESS_STATUSES:
                # Don't overwrite original finished_at
                if not self.finished_at:
                    self.finished_at = timezone.now()

                if updated_status == WorkflowExecution.Status.FAILED:
                    self.failed_attempts += 1
                elif updated_status == WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT:
                    self.timed_out_attempts += 1

                self.save()
                logger.info(f"Completed workflow execution {self.uuid} with status {updated_status}")

                self.send_alerts_if_necessary()

                return True
                # TODO: handle retry

        return updated_status not in WorkflowExecution.IN_PROGRESS_STATUSES

    def compute_updated_status(self, is_pending_transition_activation: bool = False):
        from . import WorkflowTaskInstance, WorkflowTaskInstanceExecution, WorkflowTransitionEvaluation

        if self.status != WorkflowExecution.Status.RUNNING:
            return self.status

        current_executions = list(WorkflowTaskInstanceExecution.objects.filter(
            workflow_execution=self, is_latest=True).prefetch_related('task_execution').
            exclude(task_execution__status=TaskExecution.Status.SUCCEEDED))

        updated_status_if_not_running = WorkflowExecution.Status.SUCCEEDED
        running_task_execution: Optional[TaskExecution] = None

        for wtie in current_executions:
            task_execution = wtie.task_execution
            tes = task_execution.status
            wti = wtie.workflow_task_instance

            logger.info(f"wti {wti.uuid} had task execution status {tes}")

            if tes in TaskExecution.IN_PROGRESS_STATUSES:
                running_task_execution = task_execution
            else:
                # Look at outbound transitions to see if any occurred
                was_handled = WorkflowTransitionEvaluation.objects.filter(
                        from_workflow_task_instance_execution=wtie,
                        result=True).exists()

                logger.info(f"wti {wti.uuid} status {tes} was_handled = {was_handled}")

                # TERMINATED_AFTER_TIME_OUT is first since UNSUCCESSFUL_STATUSES contains it
                if tes == TaskExecution.Status.TERMINATED_AFTER_TIME_OUT:
                    if (wti.timeout_behavior == WorkflowTaskInstance.TIMEOUT_BEHAVIOR_IGNORE) or (
                            was_handled and
                            ((wti.timeout_behavior == WorkflowTaskInstance.TIMEOUT_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED) or \
                                (wti.timeout_behavior == WorkflowTaskInstance.TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_IF_UNHANDLED))):
                        logger.debug(f"Ignoring timeout in wti {wti.uuid} since it is ignored or handled")
                    else:
                        if (wti.timeout_behavior == WorkflowTaskInstance.TIMEOUT_BEHAVIOR_FAIL_WORKFLOW_ALWAYS) or \
                            (wti.timeout_behavior == WorkflowTaskInstance.TIMEOUT_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED):
                            updated_status_if_not_running = WorkflowExecution.Status.FAILED
                        elif (wti.timeout_behavior == WorkflowTaskInstance.TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_ALWAYS) or \
                            (wti.timeout_behavior == WorkflowTaskInstance.TIMEOUT_BEHAVIOR_TIMEOUT_WORKFLOW_IF_UNHANDLED):

                            # FAILED takes precedence over TERMINATED so don't override and don't return immediately
                            if updated_status_if_not_running == WorkflowExecution.Status.RUNNING:
                                updated_status_if_not_running = WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT

                elif tes in TaskExecution.UNSUCCESSFUL_STATUSES:
                    if (wti.failure_behavior == WorkflowTaskInstance.FAILURE_BEHAVIOR_IGNORE) or (
                            (wti.failure_behavior == WorkflowTaskInstance.FAILURE_BEHAVIOR_FAIL_WORKFLOW_IF_UNHANDLED) and was_handled):
                        logger.debug(f"Ignoring failure in wti {wti.uuid} since it is ignored or handled")
                    else:
                        updated_status_if_not_running = WorkflowExecution.Status.FAILED

                        if wti.allow_workflow_execution_after_failure:
                            logger.info(f"Allowing workflow execution after failure in wti {wti.uuid}")
                        else:
                            logger.info(
                                f"Task execution {task_execution.uuid} of wtie {wtie.uuid}, wti {wti.uuid} failed, failing workflow immediately")
                            return WorkflowExecution.Status.FAILED

                if updated_status_if_not_running == WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT:
                    if wti.allow_workflow_execution_after_timeout:
                        logger.info(f"Allowing workflow execution after timeout in wti {wti.uuid}")
                    else:
                        logger.info(
                            f"Task execution {task_execution.uuid} of wtie {wtie.uuid}, wti {wti.uuid} timed out, timing out immediately")
                        return WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT

        if is_pending_transition_activation:
            logger.info('is_pending_transition_activation = True, so updated status is RUNNING')
            return WorkflowExecution.Status.RUNNING

        if running_task_execution:
            logger.info(f"Task execution {running_task_execution.uuid} is still running, keeping status as RUNNING")
            return WorkflowExecution.Status.RUNNING

        logger.info(f"compute_updated_status(): returning {updated_status_if_not_running=}")
        return updated_status_if_not_running

    def make_multidigraph_and_lookup_tables(self):
        # To handle legacy data, remove when all workflows have been converted
        from processes.serializers import WorkflowSerializer
        if not self.workflow_snapshot:
            self.workflow_snapshot = WorkflowSerializer(self.workflow,
                context=context_with_request()).data

            self.workflow_snapshot.pop('latest_workflow_execution')
            self.save()

        mdg = nx.MultiDiGraph()
        uuid_to_wti = {}
        uuid_to_wt = {}

        # For compatibility
        for wti in self.workflow_snapshot.get('workflow_process_type_instances') or self.workflow_snapshot['workflow_task_instances']:
            wti_uuid = wti['uuid']
            uuid_to_wti[wti_uuid] = wti
            mdg.add_node(wti_uuid)

        for wt in self.workflow_snapshot['workflow_transitions']:
            wt_uuid = wt['uuid']
            uuid_to_wt[wt_uuid] = wt
            mdg.add_edge((wt.get('from_workflow_process_type_instance') or \
                    wt['from_workflow_task_instance'])['uuid'],
                    (wt.get('to_workflow_process_type_instance') or \
                    wt['to_workflow_task_instance'])['uuid'])

        return [mdg, uuid_to_wti, uuid_to_wt]

    def handle_stop_requested(self):
        now = timezone.now()

        self.status = WorkflowExecution.Status.STOPPED
        self.finished_at = now

        current_user = None

        request = get_request()

        if request:
            current_user = request.user

        self.stop_running_task_executions(
            TaskExecution.StopReason.WORKFLOW_EXECUTION_STOPPED, current_user)

    def send_alerts_if_necessary(self):
        from . import AlertSendStatus, Alert, WorkflowExecutionAlert

        workflow = self.workflow

        alert_methods = workflow.alert_methods.filter(enabled=True)

        severity = DEFAULT_NOTIFICATION_SUCCESS_SEVERITY if (self.status == TaskExecution.Status.SUCCEEDED) else \
            DEFAULT_NOTIFICATION_ERROR_SEVERITY

        for am in alert_methods:
            should_send = (am.notify_on_success and (self.status == WorkflowExecution.Status.SUCCEEDED)) or \
                (am.notify_on_failure and (self.status == WorkflowExecution.Status.FAILED)) or \
                (am.notify_on_timeout and (self.status == WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT))

            if should_send:
                should_send = not WorkflowExecutionAlert.objects.filter(workflow_execution=self,
                    alert_method=am, send_status=AlertSendStatus.SUCCEEDED,
                    for_latest_execution=True).exists()

            if should_send:
                wea = WorkflowExecutionAlert(workflow_execution=self, alert_method=am)
                wea.save()

                # TODO: put the sending in a job queue to allow for retries
                try:
                    logger.info(f"Sending alert for Workflow {workflow.uuid} with status {self.status} ...")

                    wea.send_result = am.send(severity=severity, workflow_execution=self) or ''

                    if wea.send_result:
                        wea.send_result = wea.send_result[:Alert.MAX_SEND_RESULT_LENGTH]

                    logger.info(f"Done sending alert for Workflow {workflow.uuid} with status {self.status}")

                    wea.send_status = AlertSendStatus.SUCCEEDED
                    wea.completed_at = timezone.now()

                except Exception as ex:
                    logger.exception(f"Can't send using Alert Method {am.uuid} / {am.name} for Workflow Execution Alert {self.uuid}")

                    wea.send_status = AlertSendStatus.FAILED
                    wea.error_message = str(ex)[:Alert.MAX_ERROR_MESSAGE_LENGTH]

                wea.save()
            else:
                logger.debug(f"Skipping alert method {am.uuid} / {am.name}")

    def invalidate_alerts(self) -> None:
        from . import WorkflowExecutionAlert
        WorkflowExecutionAlert.objects.filter(workflow_execution=self).update(
            for_latest_execution=False)

    def clear_missing_scheduled_execution_alerts(self, mswe) -> None:
        from .alert import Alert
        from .alert_send_status import AlertSendStatus
        from .missing_scheduled_workflow_execution_alert import MissingScheduledWorkflowExecutionAlert
        from processes.serializers import MissingScheduledWorkflowExecutionSerializer

        details = MissingScheduledWorkflowExecutionSerializer(mswe,
                                                              context=context_with_request()).data

        for am in self.workflow.alert_methods.filter(
                enabled=True).exclude(error_severity_on_missing_execution='').all():
            mha = MissingScheduledWorkflowExecutionAlert(missing_scheduled_workflow_execution=mswe,
                                                         alert_method=am)
            mha.save()

            try:
                # workflow is already in details
                epoch_minutes = divmod(mswe.expected_execution_at.timestamp(), 60)[0]
                result = am.send(details=details,
                                 summary_template=self.FOUND_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE,
                                 grouping_key=f"missing_scheduled_workflow-{self.workflow.uuid}-{epoch_minutes}",
                                 is_resolution=True)
                mha.send_result = result
                mha.send_status = AlertSendStatus.SUCCEEDED
                mha.completed_at = timezone.now()
            except Exception as ex:
                logger.exception(
                    f"Failed to clear alert for missing scheduled execution of Workflow {mswe.workflow.uuid}")
                mha.send_result = ''
                mha.send_status = AlertSendStatus.FAILED
                mha.error_message = str(ex)[:Alert.MAX_ERROR_MESSAGE_LENGTH]

            mha.save()

    def handle_timeout(self) -> None:
        self.timed_out_attempts += 1

        if self.timed_out_attempts + self.failed_attempts < self.workflow.default_max_retries:
            logger.info(f"Retrying workflow execution after timeout {self.timed_out_attempts}")
            self.retry()
        else:
            logger.info(f"Stopping workflow after {self.workflow.default_max_retries} retries")
            utc_now = timezone.now()
            self.status = WorkflowExecution.Status.TERMINATED_AFTER_TIME_OUT
            self.marked_done_at = utc_now
            self.finished_at = utc_now
            self.save()

            self.stop_running_task_executions(
                TaskExecution.StopReason.WORKFLOW_EXECUTION_TIMED_OUT, current_user=None)

        self.stop_reason = WorkflowExecution.StopReason.MAX_EXECUTION_TIME_EXCEEDED

        # This will send alerts if configured by the workflow
        self.save()

    def stop_running_task_executions(self, stop_reason, current_user: Optional[User]) -> int:
        from . import WorkflowTaskInstanceExecution
        task_execution_uuids = WorkflowTaskInstanceExecution.objects.select_related(
            'task_execution').filter(workflow_execution=self, is_latest=True,
                                        task_execution__status__in=TaskExecution.IN_PROGRESS_STATUSES).\
            values_list('task_execution__uuid', flat=True)

        now = timezone.now()

        count = 0
        for te in TaskExecution.objects.filter(uuid__in=task_execution_uuids):
            try:
                te.status = TaskExecution.Status.STOPPING
                te.stop_reason = stop_reason
                te.kill_started_at = now
                te.killed_by = current_user
                te.save()
                count += 1
            except Exception:
                logger.exception("Can't save stopping task execution")

        return count

@receiver(pre_save, sender=WorkflowExecution)
def pre_save_workflow_execution(sender: Type[WorkflowExecution], **kwargs) -> None:
    instance = kwargs['instance']

    # if (instance.status == TaskExecution.Status.FAILED or \
    #     instance.status == TaskExecution.Status.TERMINATED_AFTER_TIME_OUT) and \
    #     (instance.pagerduty_event_sent_at is None):
    #     try:
    #         instance.notify_error()
    #     except Exception as ex:
    #         logger.exception(f"Can't notify after error: {instance}")

    if instance.pk is None:
        logger.info('Purging Workflow Execution history before saving new execution ...')
        num_removed = instance.workflow.purge_history(reservation_count=1)
        logger.info(f'Purged {num_removed} Workflow Executions')

    else:
        old_instance = WorkflowExecution.objects.filter(id=instance.id).first()
        if old_instance and (old_instance.status == WorkflowExecution.Status.RUNNING) and \
            (instance.status == WorkflowExecution.Status.STOPPING):
            instance.handle_stop_requested()


@receiver(post_save, sender=WorkflowExecution)
def post_save_workflow_execution(sender: Type[WorkflowExecution], **kwargs) -> None:
    instance = kwargs['instance']
    workflow = instance.workflow

    if instance.workflow.schedule:
        from processes.models import MissingScheduledWorkflowExecution
        mswe = MissingScheduledWorkflowExecution.objects.filter(
            workflow=workflow, schedule=workflow.schedule).order_by(
            '-expected_execution_at', '-id').first()

        if mswe and (not mswe.resolved_at):
            from processes.services.schedule_checker import MAX_SCHEDULED_LATENESS_SECONDS
            utc_now = timezone.now()
            lateness_seconds = (utc_now - mswe.expected_execution_at).total_seconds()
            logger.info(f"Found last missing scheduled workflow execution event {mswe.uuid}, lateness seconds = {lateness_seconds}")

            if lateness_seconds < MAX_SCHEDULED_LATENESS_SECONDS:
                logger.info(
                    f"Workflow execution {instance.uuid} is {lateness_seconds} seconds after scheduled time of {mswe.expected_execution_at}, clearing alerts")
                mswe.resolved_at = utc_now
                mswe.save()
                instance.clear_missing_scheduled_execution_alerts(mswe)
            else:
                logger.info(
                    f"Workflow execution {instance.uuid} is too far ({lateness_seconds} seconds) after scheduled time of {mswe.expected_execution_at}, not clearing alerts")
