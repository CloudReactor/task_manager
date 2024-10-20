import logging

from typing import Any

from django.db import models
from django.utils import timezone

from jinja2.sandbox import SandboxedEnvironment

from .named_with_uuid_model import NamedWithUuidModel
from .task import Task

logger = logging.getLogger(__name__)


class TaskLink(NamedWithUuidModel):
    class Meta:
        db_table = 'processes_processtypelink'
        unique_together = (('name', 'task', 'created_by_group',))
        ordering = ['rank']

    task = models.ForeignKey(Task, on_delete=models.CASCADE,
            db_column='process_type_id')
    link_url_template = models.CharField(max_length=5000)
    description = models.CharField(max_length=5000, blank=True)
    icon_url = models.CharField(max_length=1000, blank=True)
    rank = models.IntegerField(default=0)

    @property
    def link_url(self):
        if self.link_url_template.find("{{") >= 0:
            logger.debug('Processing link URL template')
            pt = self.task

            template_kwargs: dict[str, Any] = {
                'current_timestamp': round(timezone.now().timestamp()),
                'task': {
                    'uuid': str(pt.uuid),
                    'run_environment': None,
                    'name': pt.name,
                    'project_url': pt.project_url,
                    'log_query': pt.log_query,
                    'other_metadata': pt.other_metadata
                }
            }

            run_env = pt.run_environment

            if run_env:
                template_kwargs['task']['run_environment'] = {
                    'uuid': str(run_env.uuid),
                    'name': run_env.name
                }

            sandbox = SandboxedEnvironment()

            try:
                rv = sandbox.from_string(self.link_url_template).render(
                    template_kwargs)

                logger.debug(f"Processed link URL template: got '{rv}'")

                return rv
            except Exception:
                logger.warning("Can't process link URL template")
                return self.link_url_template
        else:
            return self.link_url_template
