from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from artworks.models import Artist


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.test_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'artist_name': 'Test Artist',
            'bio': 'Test bio'
        }
        self.login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

    def test_user_registration(self):
        """Test user registration endpoint"""
        response = self.client.post(
            '/api/auth/register/',
            self.test_user_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())

        # Check if artist profile was created correctly
        artist = Artist.objects.get(user__username='testuser')
        self.assertEqual(artist.name, self.test_user_data['artist_name'])
        self.assertEqual(artist.bio, self.test_user_data['bio'])

    def test_user_registration_duplicate_username(self):
        """Test registration with existing username"""
        # Create a user first with a different username
        user = User.objects.create_user(
            username='testuser',  # Use the same username as in test_user_data
            email='existing@example.com',
            password='pass123'
        )
        # Use get_or_create to avoid unique constraint violation
        Artist.objects.get_or_create(
            user=user,
            defaults={'name': 'Existing Artist'}
        )

        # Try to register with the same username
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'testuser',  # Same username
                'email': 'new@example.com',  # Different email
                'password': 'newpass123',
                'artist_name': 'New Artist',
                'bio': 'New bio'
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_user_login(self):
        """Test user login and token generation"""
        # Create a user first
        user = User.objects.create_user(
            username='loginuser',  # Changed username to avoid conflict
            email='login@example.com',
            password='testpass123'
        )
        
        # Create artist profile if it doesn't exist
        Artist.objects.get_or_create(user=user, defaults={'name': 'Test Artist'})
        
        # Use modified login data for this test
        login_data = {
            'username': 'loginuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            '/api/auth/login/',
            login_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_profile_access(self):
        """Test profile access with authentication"""
        # Register a new user which will create the artist profile
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'profileuser',  # Changed username to avoid conflict
                'email': 'profile@example.com',
                'password': 'testpass123',
                'artist_name': 'Profile Artist',
                'bio': 'Profile bio'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Login to get token
        login_data = {
            'username': 'profileuser',
            'password': 'testpass123'
        }
        response = self.client.post(
            '/api/auth/login/',
            login_data,
            format='json'
        )
        token = response.data['access']

        # Try accessing profile with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/auth/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_data = response.data['user']
        artist_data = response.data['artist']

        self.assertEqual(user_data['username'], 'profileuser')
        self.assertEqual(artist_data['name'], 'Profile Artist')

    def test_profile_access_without_auth(self):
        """Test profile access without authentication"""
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = self.client.post(
            '/api/auth/login/',
            {'username': 'wronguser', 'password': 'wrongpass'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
