from django.contrib import admin

from rest_framework.authtoken.models import TokenProxy

from typedmodels.admin import TypedModelAdmin

from .models.user_group_access_level import UserGroupAccessLevel
from .models.subscription_plan import SubscriptionPlan
from .models.subscription import Subscription
from .models.saas_token import SaasToken
from .models.run_environment import RunEnvironment
from .models.task import Task
from .models.task_execution import TaskExecution
from .models.workflow import Workflow
from .models.workflow_task_instance import WorkflowTaskInstance
from .models.workflow_execution import WorkflowExecution
from .models.workflow_transition import WorkflowTransition
from .models.workflow_task_instance_execution import WorkflowTaskInstanceExecution
from .models.workflow_transition_evaluation import WorkflowTransitionEvaluation
from .models.event import Event
from .models.missing_heartbeat_detection_event import MissingHeartbeatDetectionEvent
from .models.task_execution_status_change_event import TaskExecutionStatusChangeEvent
from .models.workflow_execution_status_change_event import WorkflowExecutionStatusChangeEvent
from .models.missing_scheduled_task_execution_event import MissingScheduledTaskExecutionEvent
from .models.missing_scheduled_workflow_execution_event import MissingScheduledWorkflowExecutionEvent
from .models.delayed_task_execution_start_event import DelayedTaskExecutionStartEvent
from .models.notification_profile import NotificationProfile
from .models.notification_delivery_method import NotificationDeliveryMethod
from .models.email_notification_delivery_method import EmailNotificationDeliveryMethod
from .models.pagerduty_notification_delivery_method import PagerDutyNotificationDeliveryMethod
from .models.notification import Notification
from .models.aws_ecs_service_load_balancer_details import AwsEcsServiceLoadBalancerDetails
from .models.user_profile import UserProfile
from .models.group_info import GroupInfo


class UserGroupAccessLevelAdmin(admin.ModelAdmin):
    search_fields = ('user__username', 'user__email', 'group__name')


class SubscriptionAdmin(admin.ModelAdmin):
    search_fields = ('subscription__name',)

class SaasTokenAdmin(admin.ModelAdmin):
    list_filter = ["group"]
    search_fields = ('key', 'name',)


class RunEnvironmentAdmin(admin.ModelAdmin):
    list_filter = ["created_by_group"]
    search_fields = ('name', 'uuid',)


class TaskAdmin(admin.ModelAdmin):
    list_filter = ["created_by_group"]
    search_fields = ('name', 'uuid', 'run_environment__name')
    readonly_fields = ('latest_task_execution',)


class TaskExecutionAdmin(admin.ModelAdmin):
    search_fields = ('uuid', 'task__name', 'task__uuid',)
    readonly_fields = ('task',)


class WorkflowAdmin(admin.ModelAdmin):
    list_filter = ["created_by_group"]
    search_fields = ('name', 'uuid',)
    readonly_fields = ('latest_workflow_execution',)


class WorkflowTaskInstanceAdmin(admin.ModelAdmin):
    search_fields = ('uuid', 'workflow__name', 'workflow__uuid', 'task__uuid',
            'task__name')
    readonly_fields = ('workflow', 'task')


class WorkflowExecutionAdmin(admin.ModelAdmin):
    search_fields = ('uuid', 'workflow__name', 'workflow__uuid',)
    readonly_fields = ('workflow',)


class WorkflowTaskInstanceExecutionAdmin(admin.ModelAdmin):
    search_fields = ('uuid', 'workflow_execution__uuid',
        'task_execution__uuid', 'workflow_execution__workflow__uuid',
        'workflow_execution__workflow__name',
        'task_execution__task__uuid', 'task_execution__task__name')
    readonly_fields = ('workflow_execution', 'workflow_task_instance',)


class WorkflowTransitionAdmin(admin.ModelAdmin):
    readonly_fields = ('from_workflow_task_instance',
                       'to_workflow_task_instance',
                      )

class WorkflowTransitionEvaluationAdmin(admin.ModelAdmin):
    readonly_fields = ('workflow_transition',
                       'from_workflow_task_instance_execution',
                       'workflow_execution',
                      )

class NotificationDeliveryMethodAdmin(TypedModelAdmin):
    list_filter = ["created_by_group"]
    search_fields = ('name', 'uuid',)


class NotificationAdmin(admin.ModelAdmin):
    list_filter = ["created_by_group"]
    search_fields = ('uuid', 'event__uuid', 'notification_delivery_method__uuid',
        'notification_profile__uuid')


class NotificationProfileAdmin(admin.ModelAdmin):
    list_filter = ["created_by_group"]
    search_fields = ('name', 'uuid',)

class EventAdmin(TypedModelAdmin):
    list_filter = ["created_by_group"]
    search_fields = ('uuid', 'grouping_key',)

class TaskEventAdmin(EventAdmin):
    search_fields = EventAdmin.search_fields + ('task__name', 'task__uuid',)

class TaskExecutionEventAdmin(TaskEventAdmin):
    search_fields = TaskEventAdmin.search_fields + ('task_execution__uuid',)

class TaskExecutionStatusChangeEventAdmin(TaskExecutionEventAdmin):
    list_filter = ["created_by_group", 'status',]

class WorkflowEventAdmin(EventAdmin):
    search_fields = EventAdmin.search_fields + ('workflow__name', 'workflow__uuid',)

class WorkflowExecutionEventAdmin(WorkflowEventAdmin):
    search_fields = WorkflowEventAdmin.search_fields + ('workflow_execution__uuid',)

class WorkflowExecutionStatusChangeEventAdmin(WorkflowExecutionEventAdmin):
    list_filter = ["created_by_group", 'status',]

admin.site.unregister(TokenProxy)
admin.site.register(UserGroupAccessLevel, UserGroupAccessLevelAdmin)
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(SaasToken, SaasTokenAdmin)
admin.site.register(RunEnvironment, RunEnvironmentAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(MissingHeartbeatDetectionEvent, TaskExecutionEventAdmin)
admin.site.register(TaskExecutionStatusChangeEvent, TaskExecutionStatusChangeEventAdmin)
admin.site.register(WorkflowExecutionStatusChangeEvent, WorkflowExecutionStatusChangeEventAdmin)
admin.site.register(MissingScheduledTaskExecutionEvent, TaskEventAdmin)
admin.site.register(MissingScheduledWorkflowExecutionEvent, WorkflowEventAdmin)
admin.site.register(DelayedTaskExecutionStartEvent, TaskExecutionEventAdmin)
admin.site.register(NotificationProfile, NotificationProfileAdmin)
admin.site.register(NotificationDeliveryMethod, NotificationDeliveryMethodAdmin)
admin.site.register(EmailNotificationDeliveryMethod, NotificationDeliveryMethodAdmin)
admin.site.register(PagerDutyNotificationDeliveryMethod, NotificationDeliveryMethodAdmin)
admin.site.register(Notification, NotificationAdmin)

admin.site.register(Task, TaskAdmin)
admin.site.register(TaskExecution, TaskExecutionAdmin)
admin.site.register(AwsEcsServiceLoadBalancerDetails)

admin.site.register(Workflow, WorkflowAdmin)
admin.site.register(WorkflowTaskInstance, WorkflowTaskInstanceAdmin)
admin.site.register(WorkflowTransition, WorkflowTransitionAdmin)
admin.site.register(WorkflowExecution, WorkflowExecutionAdmin)
admin.site.register(WorkflowTaskInstanceExecution, WorkflowTaskInstanceExecutionAdmin)
admin.site.register(WorkflowTransitionEvaluation, WorkflowTransitionEvaluationAdmin)

admin.site.register(UserProfile)
admin.site.register(GroupInfo)
