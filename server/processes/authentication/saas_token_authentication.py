from typing import cast, Tuple

from django.contrib.auth.models import User

from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import PermissionDenied

from ..models.saas_token import SaasToken


class SaasTokenAuthentication(TokenAuthentication):
    # More standard keyword that most API client generators default to
    keyword = 'Bearer'

    model = SaasToken

    def authenticate_credentials(self, key) -> Tuple[User, SaasToken]:
        (user, token) = cast(Tuple[User, SaasToken],
              super().authenticate_credentials(key))

        if (not user.is_active) or (not token.enabled):
            raise PermissionDenied(detail='Token is deactivated')

        return user, token
