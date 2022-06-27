from django.contrib import admin

from rest_framework.authtoken.models import TokenProxy

from .models import *

class SubscriptionAdmin(admin.ModelAdmin):
    search_fields = ('subscription__name',)


class RunEnvironmentAdmin(admin.ModelAdmin):
    search_fields = ('name', 'uuid',)


class TaskAdmin(admin.ModelAdmin):
    search_fields = ('name', 'uuid',)
    readonly_fields = ('latest_task_execution',)


class TaskExecutionAdmin(admin.ModelAdmin):
    search_fields = ('uuid', 'task__name', 'task__uuid',)
    readonly_fields = ('task',)


class WorkflowAdmin(admin.ModelAdmin):
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

class AlertMethodAdmin(admin.ModelAdmin):
    search_fields = ('name', 'uuid',)


class PagerDutyProfileAdmin(admin.ModelAdmin):
    search_fields = ('name', 'uuid',)


class EmailNotificationProfileAdmin(admin.ModelAdmin):
    search_fields = ('name', 'uuid',)


admin.site.unregister(TokenProxy)
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(SaasToken)
admin.site.register(RunEnvironment, RunEnvironmentAdmin)
admin.site.register(AlertMethod, AlertMethodAdmin)
admin.site.register(PagerDutyProfile, PagerDutyProfileAdmin)
admin.site.register(EmailNotificationProfile, EmailNotificationProfileAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskExecution, TaskExecutionAdmin)
admin.site.register(AwsEcsServiceLoadBalancerDetails)
admin.site.register(MissingScheduledTaskExecution)
admin.site.register(MissingScheduledTaskExecutionAlert)
admin.site.register(DelayedProcessStartDetectionEvent)
admin.site.register(DelayedProcessStartAlert)
admin.site.register(HeartbeatDetectionEvent)
admin.site.register(HeartbeatDetectionAlert)
admin.site.register(InsufficientServiceInstancesEvent)
admin.site.register(InsufficientServiceInstancesAlert)
admin.site.register(Workflow, WorkflowAdmin)
admin.site.register(WorkflowTaskInstance, WorkflowTaskInstanceAdmin)
admin.site.register(WorkflowTransition, WorkflowTransitionAdmin)
admin.site.register(WorkflowExecution, WorkflowExecutionAdmin)
admin.site.register(WorkflowTaskInstanceExecution, WorkflowTaskInstanceExecutionAdmin)
admin.site.register(WorkflowTransitionEvaluation, WorkflowTransitionEvaluationAdmin)
admin.site.register(MissingScheduledWorkflowExecution)
admin.site.register(MissingScheduledWorkflowExecutionAlert)

admin.site.register(UserProfile)
admin.site.register(GroupInfo)
