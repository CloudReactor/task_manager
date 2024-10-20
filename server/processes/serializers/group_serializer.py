from typing import Any, Optional, Sequence

import logging

from rest_framework import serializers
from rest_framework.fields import empty

from django.contrib.auth.models import Group

from processes.models import UserGroupAccessLevel


logger = logging.getLogger(__name__)


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = (
            'id', 'name', 'url', 'user_access_levels',
        )

    url = serializers.HyperlinkedIdentityField(
            view_name='groups-detail',
            lookup_field='id'
    )

    user_access_levels = serializers.SerializerMethodField()

    def __init__(self, instance=None, data=empty, include_users=True, **kwargs) -> None:
        self.include_users = include_users

        if not include_users:
            del self.fields['user_access_levels']

        super().__init__(instance, data, **kwargs)

    def get_user_access_levels(self, obj: Group) -> Optional[Sequence[dict[str, Any]]]:
        if not self.include_users:
            return None

        return [
            {
                'user': {
                    'username': ugal.user.username,
                    'email': ugal.user.email
                },
                'access_level': ugal.access_level
            } for ugal in obj.user_access_levels.all()
        ]
