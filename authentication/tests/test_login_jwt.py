from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from artworks.models import Artist
from django.urls import reverse
from datetime import timedelta
import time
import logging
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)


@override_settings(
    SIMPLE_JWT={
        'ACCESS_TOKEN_LIFETIME': timedelta(seconds=1),
        'REFRESH_TOKEN_LIFETIME': timedelta(minutes=5),
        'ROTATE_REFRESH_TOKENS': True,
        'BLACKLIST_AFTER_ROTATION': True,
        'ALGORITHM': 'HS256',
        'SIGNING_KEY': settings.SECRET_KEY,
        'AUTH_HEADER_TYPES': ('Bearer',),
        'TOKEN_TYPE_CLAIM': 'token_type',
    }
)
class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('token_obtain_pair')
        self.profile_url = reverse('profile')
        self.logout_url = reverse('logout')
        self.refresh_url = reverse('token_refresh')

        # Consistent test user data
        self.test_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'artist_name': 'Test Artist',
            'bio': 'Test artist bio'
        }

    def _register_user(self, user_data=None):
        """Helper method to register a user"""
        if user_data is None:
            user_data = self.test_user_data

        return self.client.post(
            self.register_url,
            user_data,
            format='json'
        )

    def _login_user(self, username=None, password=None):
        """Helper method to login a user and return tokens"""
        if username is None:
            username = self.test_user_data['username']
        if password is None:
            password = self.test_user_data['password']

        return self.client.post(
            self.login_url,
            {
                'username': username,
                'password': password
            },
            format='json'
        )

    def test_access_token_lifetime(self):
        """Test access token expiration"""
        # Register and login
        self._register_user()
        login_response = self._login_user()

        # Get access token
        access_token = login_response.data['access']

        # Verify token works initially
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        initial_response = self.client.get(self.profile_url)
        self.assertEqual(initial_response.status_code, status.HTTP_200_OK)

        # Wait for token to expire
        time.sleep(2)  # Wait longer than token lifetime

        # Try to access profile with expired token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        expired_response = self.client.get(self.profile_url)

        # Log detailed information
        logger.error(f"Expired token response status: {expired_response.status_code}")
        logger.error(f"Expired token response content: {expired_response.content}")

        # Verify token is no longer valid
        self.assertEqual(expired_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_blacklist(self):
        """Test token blacklisting and access token invalidation"""
        # Register a new user
        user_data = {
            'username': 'blacklistuser', 
            'email': 'blacklist@example.com',
            'password': 'testpass123',
            'artist_name': 'Blacklist Artist',
            'bio': 'Test bio'
        }
        self.client.post(self.register_url, user_data, format='json')

        # Login to get tokens
        login_response = self.client.post(
            self.login_url,
            {
                'username': 'blacklistuser',
                'password': 'testpass123'
            },
            format='json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Get tokens
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        # Create a fresh client instance to ensure no previous state
        self.client = APIClient()

        # Test access token works initially
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        initial_response = self.client.get(self.profile_url)
        self.assertEqual(initial_response.status_code, status.HTTP_200_OK)

        # Create a new client for logout
        logout_client = APIClient()

        # Logout with refresh token
        logout_response = logout_client.post(
            self.logout_url,
            {'refresh_token': refresh_token},
            format='json'
        )
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Wait a moment for blacklist to update
        time.sleep(1)

        # Try to use the original access token after logout
        # Create a fresh client instance
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = self.client.get(self.profile_url)

        # This should fail with 401 Unauthorized
        self.assertEqual(
            profile_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            "Access token should be invalid after logout"
        )
