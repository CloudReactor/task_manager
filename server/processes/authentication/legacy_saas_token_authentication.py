from .saas_token_authentication import SaasTokenAuthentication

# For deprecated method of using header Authentication: Token XXX
class LegacySaasTokenAuthentication(SaasTokenAuthentication):
    keyword = 'Token'
