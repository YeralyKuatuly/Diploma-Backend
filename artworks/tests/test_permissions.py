from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from artworks.models import Artist, Artwork, Subscription
from artworks.permissions import IsArtistOrReadOnly, IsOwnerOrReadOnly


class ArtworkPermissionsTest(APITestCase):
    def setUp(self):
        # Create test users
        self.artist_user = User.objects.create_user(
            username='artistuser',
            password='testpass123',
            email='artist@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )

        # Create test artists
        self.artist = Artist.objects.create(
            user=self.artist_user,
            name='Test Artist',
            bio='Test bio'
        )
        self.other_artist = Artist.objects.create(
            user=self.other_user,
            name='Other Artist',
            bio='Other bio'
        )

        # Create test artwork
        self.artwork = Artwork.objects.create(
            artist=self.artist,
            title='Test Artwork',
            description='Test description',
            price=100.00,
            image_url='http://example.com/test.jpg'
        )

        # Create clients
        self.artist_client = APIClient()
        self.artist_client.force_authenticate(user=self.artist_user)

        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

        self.anonymous_client = APIClient()

    def test_is_artist_or_read_only(self):
        """Test IsArtistOrReadOnly permission"""
        permission = IsArtistOrReadOnly()

        # Test with artist user
        self.assertTrue(
            permission.has_permission(self.artist_user, None)
        )

        # Test with non-artist user
        self.assertFalse(
            permission.has_permission(self.other_user, None)
        )

        # Test with anonymous user
        self.assertFalse(
            permission.has_permission(None, None)
        )

    def test_is_owner_or_read_only(self):
        """Test IsOwnerOrReadOnly permission"""
        permission = IsOwnerOrReadOnly()

        # Test with artwork owner
        self.assertTrue(
            permission.has_object_permission(
                self.artist_user,
                None,
                self.artwork
            )
        )

        # Test with non-owner
        self.assertFalse(
            permission.has_object_permission(
                self.other_user,
                None,
                self.artwork
            )
        )

        # Test with anonymous user
        self.assertFalse(
            permission.has_object_permission(
                None,
                None,
                self.artwork
            )
        )

    def test_artwork_permissions_in_api(self):
        """Test permissions in API endpoints"""
        url = reverse('artwork-detail', kwargs={'pk': self.artwork.pk})

        # Test GET (should be allowed for all)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test PATCH (should be allowed only for owner)
        data = {
            'title': 'Updated Title', 
            'image_url': 'http://example.com/updated.jpg'
        }
        response = self.artist_client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.other_client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.anonymous_client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test DELETE (should be allowed only for owner)
        response = self.artist_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Recreate artwork for next test
        self.artwork = Artwork.objects.create(
            artist=self.artist,
            title='Test Artwork',
            description='Test description',
            price=100.00,
            image_url='http://example.com/test.jpg'
        )

        url = reverse('artwork-detail', kwargs={'pk': self.artwork.pk})
        
        response = self.other_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_artwork_list_permissions(self):
        """Test permissions for artwork list endpoint"""
        url = reverse('artwork-list')

        # Test GET (should be allowed for all)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test POST (should be allowed only for artists)
        data = {
            'title': 'New Artwork',
            'description': 'New description',
            'price': 200.00,
            'artist_id': self.artist.id,
            'image_url': 'http://example.com/new.jpg'
        }

        response = self.artist_client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.other_client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.anonymous_client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SubscriptionPermissionsTest(APITestCase):
    def setUp(self):
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.artist_user = User.objects.create_user(
            username='artistuser',
            password='testpass123',
            email='artist@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )

        # Create test artists
        self.artist = Artist.objects.create(
            user=self.artist_user,
            name='Test Artist',
            bio='Test bio'
        )

        # Create clients
        self.user_client = APIClient()
        self.user_client.force_authenticate(user=self.user)

        self.artist_client = APIClient()
        self.artist_client.force_authenticate(user=self.artist_user)
        
        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)
        
        self.anonymous_client = APIClient()
        
        # Create a subscription
        self.subscription = Subscription.objects.create(
            user=self.user, 
            artist=self.artist
        )

    def test_subscription_permissions(self):
        """Test only authenticated users can subscribe/unsubscribe"""
        # Test subscribing - authenticated
        url = reverse('artist-subscribe', kwargs={'pk': self.artist.pk})
        response = self.other_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Test subscribing - unauthenticated
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test unsubscribing - authenticated owner
        url = reverse('artist-unsubscribe', kwargs={'pk': self.artist.pk})
        response = self.user_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Re-create the subscription
        self.subscription = Subscription.objects.create(
            user=self.user, 
            artist=self.artist
        )
        
        # Test unsubscribing - other user (not subscribed)
        response = self.other_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test unsubscribing - unauthenticated
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 