from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from artworks.models import Artist, Artwork


class DeleteAccountTest(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Create test artist
        self.artist = Artist.objects.create(
            user=self.user,
            name='Test Artist',
            bio='Test bio'
        )
        
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
        
        # Create another user for testing unauthorized access
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )
        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

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
        response = self.other_client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify user and associated data still exist
        self.assertTrue(User.objects.filter(id=self.user.id).exists())
        self.assertTrue(Artist.objects.filter(id=self.artist.id).exists())
        self.assertEqual(Artwork.objects.filter(artist=self.artist).count(), 2)

    def test_delete_account_not_authenticated(self):
        """Test that unauthenticated users cannot delete accounts"""
        url = reverse('delete-account')
        response = self.client.delete(url)
        
        # First verify the request works when authenticated
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
        
        # Simulate an error during deletion by raising an exception
        def mock_delete(*args, **kwargs):
            raise Exception("Simulated error")
        
        # Temporarily replace the delete method to simulate an error
        original_delete = User.delete
        User.delete = mock_delete
        
        try:
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            
            # Verify nothing was deleted due to transaction rollback
            self.assertTrue(User.objects.filter(id=self.user.id).exists())
            self.assertTrue(Artist.objects.filter(id=self.artist.id).exists())
            self.assertEqual(Artwork.objects.filter(artist=self.artist).count(), 2)
        finally:
            # Restore the original delete method
            User.delete = original_delete 