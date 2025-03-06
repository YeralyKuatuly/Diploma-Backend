from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from artworks.models import Artist, Artwork
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
            price=100.00
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
            'artist_id': self.artist.id
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Artwork.objects.count(), 2)
        self.assertEqual(response.data['title'], 'New Artwork')

    def test_create_artwork_unauthorized(self):
        """Test creating artwork for another artist"""
        url = reverse('artwork-list')
        data = {
            'title': 'New Artwork',
            'description': 'New description',
            'price': 200.00,
            'artist_id': self.other_artist.id
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

    def test_update_artwork(self):
        """Test updating an artwork"""
        url = reverse('artwork-detail', kwargs={'pk': self.artwork.pk})
        data = {
            'title': 'Updated Artwork',
            'description': 'Updated description',
            'price': 150.00
        }

        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Artwork')
        self.assertEqual(response.data['price'], '150.00')

    def test_update_artwork_unauthorized(self):
        """Test updating another artist's artwork"""
        # Create artwork for other artist
        other_artwork = Artwork.objects.create(
            artist=self.other_artist,
            title='Other Artwork',
            description='Other description',
            price=300.00
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
            price=300.00
        )

        url = reverse('artwork-detail', kwargs={'pk': other_artwork.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Artwork.objects.count(), 2)

    def test_artwork_with_image(self):
        """Test creating and updating artwork with image"""
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
            'image': image
        }

        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['image'])

        # Clean up the test image file
        if os.path.exists(response.data['image']):
            os.remove(response.data['image'])

    def test_artwork_count_update(self):
        """Test that artist's artwork count is updated when artwork is created/deleted"""
        # Create new artwork
        url = reverse('artwork-list')
        data = {
            'title': 'New Artwork',
            'description': 'New description',
            'price': 200.00,
            'artist_id': self.artist.id
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
