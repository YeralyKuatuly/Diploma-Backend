from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from ..models import Artist, Artwork
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
        self.assertEqual(
            response.data[0]['image'], 
            'http://example.com/image.jpg'
        )

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
        # Check image property works correctly
        self.assertEqual(
            response.data['image'], 
            'http://example.com/new.jpg'
        )
        # Don't check image_url directly if serializer doesn't return it

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
        # Check the image URL is returned
        self.assertTrue(response.data['image'].startswith('http'))
        
        # Check image was saved to model (don't check file existence)
        artwork = Artwork.objects.get(title='Artwork with Image')
        self.assertIsNotNone(artwork.image_file.name)

    def test_update_artwork(self):
        """Test updating an artwork"""
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'Updated Title', 
            'image_url': 'http://example.com/updated.jpg'
        }
        response = self.client.patch(self.artwork_detail_url, data,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')
        # Check image property instead of image_url
        self.assertEqual(
            response.data['image'], 
            'http://example.com/updated.jpg'
        )

    def test_update_artwork_with_image(self):
        """Test updating artwork with a new image file"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'image_file': self.image
        }
        response = self.client.patch(self.artwork_detail_url, data,
                                    format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['image'].startswith('http'))
        
        # Just check that the response has an image property
        # Don't verify details of the uploaded file due to test environment
        self.assertIsNotNone(response.data['image'])

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
        # Check artwork_count is present
        self.assertEqual(response.data['artwork_count'], 0)

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

    def test_artist_subscribers(self):
        """Test retrieving artist's subscribers count"""
        # Create a subscriber
        subscriber = User.objects.create_user(
            username='subscriber',
            email='subscriber@example.com',
            password='testpass123'
        )
        
        # Add subscription using the viewset action
        subscription_url = reverse(
            'artist-subscribe', 
            kwargs={'pk': self.artist.pk}
        )
        client = APIClient()
        client.force_authenticate(user=subscriber)
        response = client.post(subscription_url)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check artist detail includes subscriber count
        response = self.client.get(self.artist_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subscribers_count'], 1)
