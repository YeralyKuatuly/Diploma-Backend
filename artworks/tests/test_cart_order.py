from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from artworks.models import Artist, Artwork, Cart, CartItem, Order, OrderItem
from decimal import Decimal


class CartAndOrderTests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

        # Create artist user
        self.artist_user = User.objects.create_user(
            username='artist',
            password='testpass123',
            email='artist@example.com'
        )
        
        # Get or create the artist (should be created by signal)
        try:
            self.artist = Artist.objects.get(user=self.artist_user)
            # Update name and bio if needed
            self.artist.name = 'Test Artist'
            self.artist.bio = 'Test bio'
            self.artist.save()
        except Artist.DoesNotExist:
            self.artist = Artist.objects.create(
                user=self.artist_user,
                name='Test Artist',
                bio='Test bio'
            )

        # Create artwork
        self.artwork = Artwork.objects.create(
            artist=self.artist,
            title='Test Artwork',
            description='Test description',
            price=100.00,
            image_url='http://example.com/test.jpg'
        )

        # Create another artwork
        self.artwork2 = Artwork.objects.create(
            artist=self.artist,
            title='Test Artwork 2',
            description='Test description 2',
            price=200.00,
            image_url='http://example.com/test2.jpg'
        )

        # Create client and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_add_to_cart(self):
        """Test adding an item to cart"""
        url = reverse('cart-add-item', kwargs={'pk': 'me'})
        data = {
            'artwork_id': self.artwork.id,
            'quantity': 2
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if cart was created
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        
        # Check if cart item was created
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        
        # Check cart item details
        cart_item = cart.items.first()
        self.assertEqual(cart_item.artwork, self.artwork)
        self.assertEqual(cart_item.quantity, 2)
        
        # Check cart total price
        self.assertEqual(cart.total_price, Decimal('200.00'))

    def test_remove_from_cart(self):
        """Test removing an item from cart"""
        # First add an item to cart
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, artwork=self.artwork, quantity=2)
        
        url = reverse('cart-remove-item', kwargs={'pk': 'me'})
        data = {
            'artwork_id': self.artwork.id,
            'quantity': 2  # Match the quantity to ensure full removal
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if cart item was removed
        self.assertEqual(cart.items.count(), 0)

    def test_update_cart_item_quantity(self):
        """Test updating quantity of a cart item"""
        # First add an item to cart
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart, 
            artwork=self.artwork, 
            quantity=1
        )
        
        url = reverse('cart-add-item', kwargs={'pk': 'me'})
        data = {
            'artwork_id': self.artwork.id,
            'quantity': 2
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if quantity was updated
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)
        
        # Check cart total price
        self.assertEqual(cart.total_price, Decimal('300.00'))

    def test_clear_cart(self):
        """Test clearing the cart"""
        # First add items to cart
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, artwork=self.artwork, quantity=2)
        CartItem.objects.create(cart=cart, artwork=self.artwork2, quantity=1)
        
        url = reverse('cart-clear', kwargs={'pk': 'me'})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if cart was cleared
        self.assertEqual(cart.items.count(), 0)

    def test_get_cart(self):
        """Test retrieving cart details"""
        # First add items to cart
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, artwork=self.artwork, quantity=2)
        CartItem.objects.create(cart=cart, artwork=self.artwork2, quantity=1)
        
        url = reverse('cart-detail', kwargs={'pk': 'me'})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response data
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(response.data['total_price'], '400.00')

    def test_create_order(self):
        """Test creating an order from cart"""
        # First add items to cart
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, artwork=self.artwork, quantity=2)
        CartItem.objects.create(cart=cart, artwork=self.artwork2, quantity=1)
        
        url = reverse('order-list')
        data = {
            'shipping_address': '123 Test St, Test City, TC 12345'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if order was created
        self.assertTrue(Order.objects.filter(user=self.user).exists())
        
        # Check order details
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.total_amount, Decimal('400.00'))
        self.assertEqual(
            order.shipping_address, 
            '123 Test St, Test City, TC 12345'
        )
        self.assertEqual(order.status, 'pending')
        
        # Check if cart was cleared
        self.assertEqual(cart.items.count(), 0)

    def test_cancel_order(self):
        """Test cancelling an order"""
        # First create an order
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('300.00'),
            shipping_address='123 Test St, Test City, TC 12345',
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            artwork=self.artwork,
            price=Decimal('100.00'),
            quantity=3
        )
        
        url = reverse('order-cancel', kwargs={'pk': order.id})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if order status was updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_get_orders(self):
        """Test retrieving all orders for a user"""
        # Create some orders
        order1 = Order.objects.create(
            user=self.user,
            total_amount=Decimal('300.00'),
            shipping_address='123 Test St, Test City, TC 12345',
            status='pending'
        )
        OrderItem.objects.create(
            order=order1,
            artwork=self.artwork,
            price=Decimal('100.00'),
            quantity=3
        )
        
        order2 = Order.objects.create(
            user=self.user,
            total_amount=Decimal('200.00'),
            shipping_address='123 Test St, Test City, TC 12345',
            status='processing'
        )
        OrderItem.objects.create(
            order=order2,
            artwork=self.artwork2,
            price=Decimal('200.00'),
            quantity=1
        )
        
        url = reverse('order-list')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response data
        self.assertEqual(len(response.data), 2)
        
        # Check that both orders are in the response
        order_ids = [item['id'] for item in response.data]
        self.assertIn(order1.id, order_ids)
        self.assertIn(order2.id, order_ids)

    def test_get_order_detail(self):
        """Test retrieving details of a specific order"""
        # First create an order
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('300.00'),
            shipping_address='123 Test St, Test City, TC 12345',
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            artwork=self.artwork,
            price=Decimal('100.00'),
            quantity=3
        )
        
        url = reverse('order-detail', kwargs={'pk': order.id})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response data
        self.assertEqual(response.data['id'], order.id)
        self.assertEqual(response.data['total_amount'], '300.00')
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['quantity'], 3)
        self.assertEqual(response.data['items'][0]['price'], '100.00') 