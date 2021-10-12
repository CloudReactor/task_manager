from django.utils import timezone

from processes.models import GroupInfo

import factory

from pytest_factoryboy import register


from .group_factory import GroupFactory


@register
class GroupInfoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupInfo

    group = factory.SubFactory(GroupFactory)
    api_credits_used_current_month = 0
    api_credits_used_previous_month = 500
    api_last_used_at = timezone.now()
    updated_at = timezone.now()
