from typing import Dict

from django.contrib.auth.models import User

from rest_framework import serializers
from rest_framework.fields import empty

from processes.models import UserProfile
from processes.models.user_group_access_level import UserGroupAccessLevel

from .group_serializer import GroupSerializer


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ()


class UserSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(many=False)

    class Meta:
        model = User
        fields = (
                'username', 'email',
                'first_name', 'last_name', 'date_joined',
                'groups', 'group_access_levels', 'user_profile',
        )

    username = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    date_joined = serializers.ReadOnlyField()

    groups = GroupSerializer(many=True, read_only=True, include_users=False)
    group_access_levels = serializers.SerializerMethodField()

    def __init__(self, instance=None, data=empty, include_groups=False,
            include_profile=False, **kwargs) -> None:
        if not include_groups:
            del self.fields['groups']
            del self.fields['group_access_levels']

        if not include_profile:
            del self.fields['user_profile']

        super().__init__(instance, data, **kwargs)

    def get_group_access_levels(self, user: User) -> Dict[int, int]:
        rv: Dict[int, int] = {
                ugal.group.id : ugal.access_level for ugal in
                UserGroupAccessLevel.objects.filter(user=user)
        }

        # If a user has access level OBSERVER, it is omitted from
        # UserGroupAccessLevel. So set it for any groups not in the
        # return value.
        for g in user.groups.all():
            if rv.get(g.id) is None:
                rv[g.id] = UserGroupAccessLevel.ACCESS_LEVEL_OBSERVER

        return rv

    def to_internal_value(self, data):
        keys = data.keys()
        for key in ['username', 'password', 'email', 'date_joined']:
            if key in keys:
                raise serializers.ValidationError({key: [
                    f'{key} cannot be set with this endpoint'
                ]})

        return super().to_internal_value(data)


class FullUserSerializer(UserSerializer):
    def __init__(self, instance=None, data=empty, **kwargs) -> None:
        super().__init__(instance, data, include_groups=True,
                include_profile=True, **kwargs)
