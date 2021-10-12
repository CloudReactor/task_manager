from django.http import JsonResponse

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import PermissionDenied

from processes.models.user_group_access_level import UserGroupAccessLevel

from ..models import SaasToken
from ..serializers import UserSerializer
from ..authentication import SaasTokenAuthentication


# TODO: this is no longer being used, remove
class CustomAuthToken(ObtainAuthToken):
    authentication_classes = (SaasTokenAuthentication,)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        access_level = UserGroupAccessLevel.access_level_for_user_in_group(user=user,
                group=user.groups.first())

        if not access_level:
            raise PermissionDenied()

        token, _created = SaasToken.objects.get_or_create(
                user=user, group=user.groups.first(),
                access_level=access_level)
        serializer = UserSerializer(user)
        return JsonResponse({'token': token.key, 'user': serializer.data})
