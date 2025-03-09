from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from artworks.models import Artist, Artwork
from authentication.serializers import RegisterSerializer
from authentication.views import DeleteAccountView


class DeleteAccountTest(APITestCase):
    def setUp(self):
        # Clean up any existing data
        User.objects.all().delete()
        Artist.objects.all().delete()
        Artwork.objects.all().delete()

        # Create test user with artist profile
        register_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'artist_name': 'Test Artist',
            'bio': 'Test bio'
        }
        serializer = RegisterSerializer(data=register_data)
        serializer.is_valid(raise_exception=True)
        self.user = serializer.save()
        self.artist = Artist.objects.get(user=self.user)

        # Create test artworks
        self.artwork1 = Artwork.objects.create(
            artist=self.artist,
            title='Artwork 1',
            description='Description 1',
            price=100.00
        )
        self.artwork2 = Artwork.objects.create(
            artist=self.artist,
            title='Artwork 2',
            description='Description 2',
            price=200.00
        )

        # Create client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create another user with artist profile
        register_data = {
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': 'testpass123',
            'artist_name': 'Other Artist',
            'bio': 'Other bio'
        }
        serializer = RegisterSerializer(data=register_data)
        serializer.is_valid(raise_exception=True)
        self.other_user = serializer.save()
        self.other_artist = Artist.objects.get(user=self.other_user)

        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

    def tearDown(self):
        # Clean up after each test
        User.objects.all().delete()
        Artist.objects.all().delete()
        Artwork.objects.all().delete()

    def test_delete_account(self):
        """Test deleting a user account with associated data"""
        url = reverse('delete-account')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify user is deleted
        self.assertFalse(User.objects.filter(id=self.user.id).exists())

        # Verify artist is deleted
        self.assertFalse(Artist.objects.filter(id=self.artist.id).exists())

        # Verify artworks are deleted
        self.assertEqual(Artwork.objects.filter(artist=self.artist).count(), 0)

    def test_delete_account_unauthorized(self):
        """Test that unauthorized users cannot delete accounts"""
        url = reverse('delete-account')
        # Try to delete the first user's account while authenticated as the second user
        response = self.other_client.delete(url, {'user_id': self.user.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify user and associated data still exist
        self.assertTrue(User.objects.filter(id=self.user.id).exists())
        self.assertTrue(Artist.objects.filter(id=self.artist.id).exists())
        self.assertEqual(Artwork.objects.filter(artist=self.artist).count(), 2)

    def test_delete_account_not_authenticated(self):
        """Test that unauthenticated users cannot delete accounts"""
        url = reverse('delete-account')

        # First verify the request works when authenticated
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Now try without authentication
        self.client.force_authenticate(user=None)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_account_without_artist_profile(self):
        """Test deleting a user account without an artist profile"""
        # Create a user without an artist profile
        user_without_artist = User.objects.create_user(
            username='noartist',
            password='testpass123',
            email='noartist@example.com'
        )

        # Authenticate as this user
        self.client.force_authenticate(user=user_without_artist)

        url = reverse('delete-account')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=user_without_artist.id).exists())

    def test_delete_account_transaction(self):
        """Test that account deletion is atomic (all-or-nothing)"""
        url = reverse('delete-account')

        # Create a mock that raises an exception
        def mock_delete(*args, **kwargs):
            raise Exception("Simulated error")

        # Store the original delete method
        original_delete = Artist.delete

        try:
            # Replace the delete method with our mock
            Artist.delete = mock_delete

            # Attempt to delete the account
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            # Verify nothing was deleted due to transaction rollback
            self.assertTrue(User.objects.filter(id=self.user.id).exists())
            self.assertTrue(Artist.objects.filter(id=self.artist.id).exists())
            self.assertEqual(Artwork.objects.filter(artist=self.artist).count(), 2)
        finally:
            # Restore the original delete method
            Artist.delete = original_delete
