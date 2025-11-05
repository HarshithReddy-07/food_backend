# api/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import User
import jwt
from django.utils import timezone
import datetime

class JWTGoogleAuthentication(BaseAuthentication):
    """
    Custom authentication class to decode JWT and find user by googleId.
    Replaces the logic in Node.js's `auth.js` middleware.
    """
    # api/authentication.py

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import User
import jwt
# ... (other imports)

class JWTGoogleAuthentication(BaseAuthentication):
    """
    Custom authentication class defensively retrieving the JWT from the request.
    """
    def get_auth_header(self, request):
        # 1. Try DRF standard (preferred, standardizes casing)
        auth_header = request.headers.get('Authorization')
        
        # 2. If not found, try raw Django server environment (fallback for Gunicorn/ASGI)
        if not auth_header:
            # Django server environment converts header names to uppercase,
            # replaces hyphens with underscores, and adds an HTTP_ prefix.
            auth_header = request.META.get('HTTP_AUTHORIZATION')

        return auth_header

    def authenticate(self, request):
        auth_header = self.get_auth_header(request)
        
        # Check 1: Is the header present and does it start with 'Bearer '?
        if not auth_header or not auth_header.startswith('Bearer '):
            # Returns None, which DRF converts to "Authentication credentials were not provided."
            return None 
        
        # Extract the token
        token = auth_header.split(' ')[1]
        print("token:",token)
        try:
            # Verify the JWT using your shared secret key
            decoded_payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            
            google_id = decoded_payload.get('googleId')
            if not google_id:
                raise AuthenticationFailed('Token payload missing googleId')

            # Find user and return
            user = User.objects.get(googleId=google_id)
            return (user, token) 

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')
        except Exception:
            raise AuthenticationFailed('Invalid token')