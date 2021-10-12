from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

class AllowBadJwtTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        '''
        Base implementation throws an exception if the token is invalid,
        we just want it to continue when that's the case.
        '''

        try:
            return super().authenticate(request)
        except InvalidToken:
            return None
