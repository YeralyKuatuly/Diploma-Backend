from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from artworks.models import Artist, Artwork, Subscription, Notification
from django.core.files.uploadedfile import SimpleUploadedFile
import os


class ArtworkViewsTest(APITestCase):
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

        # Create another user and artist for testing permissions
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
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

        # Create client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create another client for the other user
        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

    def test_list_artworks(self):
        """Test listing all artworks"""
        url = reverse('artwork-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Test Artwork')

    def test_create_artwork(self):
        """Test creating a new artwork"""
        url = reverse('artwork-list')
        data = {
            'title': 'New Artwork',
            'description': 'New description',
            'price': 200.00,
            'artist_id': self.artist.id,
            'image_url': 'http://example.com/new.jpg'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Artwork.objects.count(), 2)
        self.assertEqual(response.data['title'], 'New Artwork')
        self.assertEqual(
            response.data['image'], 
            'http://example.com/new.jpg'
        )

    def test_create_artwork_unauthorized(self):
        """Test creating artwork for another artist"""
        url = reverse('artwork-list')
        data = {
            'title': 'New Artwork',
            'description': 'New description',
            'price': 200.00,
            'artist_id': self.other_artist.id,
            'image_url': 'http://example.com/new.jpg'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Artwork.objects.count(), 1)

    def test_retrieve_artwork(self):
        """Test retrieving a single artwork"""
        url = reverse('artwork-detail', kwargs={'pk': self.artwork.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Artwork')
        self.assertEqual(
            response.data['image'], 
            'http://example.com/test.jpg'
        )

    def test_update_artwork(self):
        """Test updating an artwork"""
        url = reverse('artwork-detail', kwargs={'pk': self.artwork.pk})
        data = {
            'title': 'Updated Artwork',
            'description': 'Updated description',
            'price': 150.00,
            'image_url': 'http://example.com/updated.jpg'
        }

        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Artwork')
        self.assertEqual(response.data['price'], '150.00')
        self.assertEqual(
            response.data['image'], 
            'http://example.com/updated.jpg'
        )

    def test_update_artwork_unauthorized(self):
        """Test updating another artist's artwork"""
        # Create artwork for other artist
        other_artwork = Artwork.objects.create(
            artist=self.other_artist,
            title='Other Artwork',
            description='Other description',
            price=300.00,
            image_url='http://example.com/other.jpg'
        )

        url = reverse('artwork-detail', kwargs={'pk': other_artwork.pk})
        data = {
            'title': 'Updated Artwork',
            'description': 'Updated description',
            'price': 350.00
        }

        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        other_artwork.refresh_from_db()
        self.assertEqual(other_artwork.title, 'Other Artwork')
        self.assertEqual(other_artwork.price, 300.00)

    def test_delete_artwork(self):
        """Test deleting an artwork"""
        url = reverse('artwork-detail', kwargs={'pk': self.artwork.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Artwork.objects.count(), 0)

    def test_delete_artwork_unauthorized(self):
        """Test deleting another artist's artwork"""
        # Create artwork for other artist
        other_artwork = Artwork.objects.create(
            artist=self.other_artist,
            title='Other Artwork',
            description='Other description',
            price=300.00,
            image_url='http://example.com/other.jpg'
        )

        url = reverse('artwork-detail', kwargs={'pk': other_artwork.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Artwork.objects.count(), 2)

    def test_artwork_with_image_file(self):
        """Test creating and updating artwork with image file"""
        # Create a test image file
        image_content = (
            b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,'
            b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        image = SimpleUploadedFile(
            "test.gif",
            image_content,
            content_type="image/gif"
        )

        # Test creating artwork with image
        url = reverse('artwork-list')
        data = {
            'title': 'Artwork with Image',
            'description': 'Description',
            'price': 100.00,
            'artist_id': self.artist.id,
            'image_file': image
        }

        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Image property should return a URL
        self.assertTrue(response.data['image'])
        
        # Get the created artwork
        created_artwork = Artwork.objects.get(title='Artwork with Image')
        self.assertIsNotNone(created_artwork.image_file)

        # Clean up the test image file if it exists
        if (created_artwork.image_file and 
                os.path.exists(created_artwork.image_file.path)):
            os.remove(created_artwork.image_file.path)

    def test_artwork_count_update(self):
        """Test artist's artwork count updates on create/delete"""
        # Create new artwork
        url = reverse('artwork-list')
        data = {
            'title': 'New Artwork',
            'description': 'New description',
            'price': 200.00,
            'artist_id': self.artist.id,
            'image_url': 'http://example.com/new.jpg'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check artwork count
        self.artist.refresh_from_db()
        self.assertEqual(self.artist.artwork_count, 2)

        # Delete artwork
        url = reverse('artwork-detail', kwargs={'pk': self.artwork.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check artwork count again
        self.artist.refresh_from_db()
        self.assertEqual(self.artist.artwork_count, 1)


class SubscriptionTest(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        # Create test artist
        self.artist_user = User.objects.create_user(
            username='artist',
            password='testpass123',
            email='artist@example.com'
        )
        self.artist = Artist.objects.create(
            user=self.artist_user,
            name='Test Artist',
            bio='Test bio'
        )

        # Create client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_subscribe_to_artist(self):
        """Test subscribing to an artist"""
        url = reverse('artist-subscribe', kwargs={'pk': self.artist.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Subscription.objects.filter(
                user=self.user, artist=self.artist
            ).exists()
        )

    def test_unsubscribe_from_artist(self):
        """Test unsubscribing from an artist"""
        # First subscribe
        Subscription.objects.create(user=self.user, artist=self.artist)
        
        url = reverse('artist-unsubscribe', kwargs={'pk': self.artist.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Subscription.objects.filter(
                user=self.user, artist=self.artist
            ).exists()
        )

    def test_subscribe_twice(self):
        """Test subscribing to an artist twice"""
        # First subscribe
        Subscription.objects.create(user=self.user, artist=self.artist)
        
        url = reverse('artist-subscribe', kwargs={'pk': self.artist.pk})
        response = self.client.post(url)

        # Should return conflict or bad request
        self.assertIn(
            response.status_code, 
            [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
        )
        
        # Still only one subscription should exist
        self.assertEqual(
            Subscription.objects.filter(
                user=self.user, artist=self.artist
            ).count(), 
            1
        )


class NotificationTest(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        # Create test artist
        self.artist_user = User.objects.create_user(
            username='artist',
            password='testpass123',
            email='artist@example.com'
        )
        self.artist = Artist.objects.create(
            user=self.artist_user,
            name='Test Artist',
            bio='Test bio'
        )

        # Create subscription
        Subscription.objects.create(user=self.user, artist=self.artist)

        # Create client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_notification_created_on_artwork_upload(self):
        """Test notification creation when artist uploads artwork"""
        # Authenticate as the artist
        self.client.force_authenticate(user=self.artist_user)
        
        # Upload artwork
        url = reverse('artwork-list')
        data = {
            'title': 'New Artwork',
            'description': 'New description',
            'price': 200.00,
            'artist_id': self.artist.id,
            'image_url': 'http://example.com/new.jpg'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check notification was created for the subscriber
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                notification_type=Notification.ARTWORK_ADDED,
                artist=self.artist
            ).exists()
        )

    def test_list_notifications(self):
        """Test listing notifications for user"""
        # Create a notification
        artwork = Artwork.objects.create(
            artist=self.artist,
            title='Test Artwork',
            description='Test description',
            price=100.00,
            image_url='http://example.com/test.jpg'
        )
        
        Notification.objects.create(
            user=self.user,
            notification_type=Notification.ARTWORK_ADDED,
            content=f"New artwork by {self.artist.name}",
            artwork=artwork,
            artist=self.artist
        )
        
        # Authenticate as the user
        self.client.force_authenticate(user=self.user)
        
        # Get notifications
        url = reverse('notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['notification_type'], 
            Notification.ARTWORK_ADDED
        )
        
    def test_mark_notification_as_read(self):
        """Test marking a notification as read"""
        # Create a notification
        artwork = Artwork.objects.create(
            artist=self.artist,
            title='Test Artwork',
            description='Test description',
            price=100.00,
            image_url='http://example.com/test.jpg'
        )
        
        notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.ARTWORK_ADDED,
            content=f"New artwork by {self.artist.name}",
            artwork=artwork,
            artist=self.artist
        )
        
        # Authenticate as the user
        self.client.force_authenticate(user=self.user)
        
        # Mark notification as read
        url = reverse('notification-mark-read', kwargs={'pk': notification.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
