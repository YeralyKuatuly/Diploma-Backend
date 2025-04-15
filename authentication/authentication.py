from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from django.utils.translation import gettext_lazy as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class that checks for blacklisted tokens
    and provides specific error messages.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token)
        or None if authentication fails.
        """
        try:
            # First get the standard JWT authentication result
            result = super().authenticate(request)
            if not result:
                return None
            
            user, token = result
            
            # Check if the token has been blacklisted
            if hasattr(token, 'payload') and 'jti' in token.payload:
                jti = token.payload['jti']
                if BlacklistedToken.objects.filter(token__jti=jti).exists():
                    raise AuthenticationFailed({
                        'code': 'token_blacklisted',
                        'detail': _('Token is blacklisted'),
                    })
            
            return result
            
        except InvalidToken as e:
            raise AuthenticationFailed({
                'code': 'token_expired',
                'detail': _('Token has expired'),
            })
        except Exception as e:
            raise AuthenticationFailed({
                'code': 'authentication_failed',
                'detail': str(e),
            })

    def get_header(self, request):
        header = super().get_header(request)
        if header is None:
            return None
        return header


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = CustomJWTAuthentication
    name = 'JWT Authentication'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        } 