from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Artist, Artwork
import tempfile
from PIL import Image


class ArtworkTests(APITestCase):
    def setUp(self):
        # Create test user and artist
        self.user = User.objects.create_user(
            username='testartist',
            email='artist@example.com',
            password='testpass123'
        )
        self.artist = Artist.objects.get(user=self.user)

        self.artwork = Artwork.objects.create(
            title='Test Artwork',
            description='Test Description',
            price='99.99',
            artist=self.artist,
            image_url='http://example.com/image.jpg'
        )

        self.image = self.generate_test_image()

        self.artwork_list_url = reverse('artwork-list')
        self.artwork_detail_url = reverse('artwork-detail',
                                          kwargs={'pk': self.artwork.pk})

    def generate_test_image(self):
        """Generate a test image for testing file uploads"""
        image = Image.new('RGB', (100, 100), color='red')
        tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg')
        image.save(tmp_file)
        tmp_file.seek(0)
        return tmp_file

    def test_list_artworks(self):
        """Test retrieving list of artworks"""
        response = self.client.get(self.artwork_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_artwork(self):
        """Test creating a new artwork"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New Artwork',
            'description': 'New Description',
            'price': '149.99',
            'artist_id': self.artist.id,
            'image_url': 'http://example.com/new.jpg'
        }
        response = self.client.post(self.artwork_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Artwork.objects.count(), 2)

    def test_create_artwork_with_image(self):
        """Test creating artwork with image upload"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'Artwork with Image',
            'description': 'Test Description',
            'price': '199.99',
            'artist_id': self.artist.id,
            'image_file': self.image
        }
        response = self.client.post(self.artwork_list_url, data,
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['image'].startswith('http'))

    def test_update_artwork(self):
        """Test updating an artwork"""
        self.client.force_authenticate(user=self.user)
        data = {'title': 'Updated Title'}
        response = self.client.patch(self.artwork_detail_url, data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

    def test_delete_artwork(self):
        """Test deleting an artwork"""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.artwork_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Artwork.objects.count(), 0)


class ArtistTests(APITestCase):
    def setUp(self):
        # Create test user and artist
        self.user = User.objects.create_user(
            username='testartist',
            email='artist@example.com',
            password='testpass123'
        )
        self.artist = Artist.objects.get(user=self.user)

        self.artist_list_url = reverse('artist-list')
        self.artist_detail_url = reverse(
            'artist-detail', kwargs={'pk': self.artist.pk})

    def test_list_artists(self):
        """Test retrieving list of artists"""
        response = self.client.get(self.artist_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_artist_detail(self):
        """Test retrieving artist details"""
        response = self.client.get(self.artist_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.user.username)

    def test_update_artist(self):
        """Test updating artist profile"""
        self.client.force_authenticate(user=self.user)
        data = {
            'name': 'Updated Name',
            'bio': 'Updated Bio'
        }
        response = self.client.patch(self.artist_detail_url, data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Name')
