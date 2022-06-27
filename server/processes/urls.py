from django.urls import include, path

from rest_framework import routers

from . import views

class OptionalSlashRouter(routers.DefaultRouter):
    """
    Makes the trailing slash in URL's optional:

    https://stackoverflow.com/questions/46163838/how-can-i-make-a-trailing-slash-optional-on-a-django-rest-framework-simplerouter

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = '/?'


router = OptionalSlashRouter()
router.register(r'users', views.UserViewSet,
                basename='users')
router.register(r'groups', views.GroupViewSet,
                basename='groups')
router.register(r'group_memberships', views.GroupMembershipViewSet,
                basename='group_memberships')
router.register(r'api_keys', views.SaasTokenViewSet,
                basename='api_keys')
router.register(r'invitations', views.InvitationViewSet,
                basename='invitations')
router.register(r'alert_methods', views.AlertMethodViewSet,
                basename='alert_methods')
router.register(r'email_notification_profiles',
        views.EmailNotificationProfileViewSet,
        basename='email_notification_profiles')
router.register(r'pagerduty_profiles',
        views.PagerDutyProfileViewSet, basename='pagerduty_profiles')

# Deprecated
router.register(r'process_types', views.TaskViewSet,
                basename='process_types')

router.register(r'tasks', views.TaskViewSet,
                basename='tasks')

# Deprecated
router.register(r'process_executions',
        views.TaskExecutionViewSet, basename='process_executions')

router.register(r'task_executions',
        views.TaskExecutionViewSet, basename='task_executions')

router.register(r'workflows',
        views.WorkflowViewSet, basename='workflows')

router.register(r'workflow_task_instances',
        views.WorkflowTaskInstanceViewSet, basename='workflow_task_instances')
router.register(r'workflow_transitions',
        views.WorkflowTransitionViewSet, basename='workflow_transitions')
router.register(r'workflow_executions', views.WorkflowExecutionViewSet,
        basename='workflow_executions')
router.register(r'run_environments', views.RunEnvironmentViewSet,
        basename='run_environments')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
