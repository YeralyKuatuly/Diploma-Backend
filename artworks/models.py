from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone


class Artist(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='artist_profile'
    )
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(
        upload_to='artist_profiles/',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    artwork_count = models.IntegerField(default=0)
    subscribers_count = models.IntegerField(default=0)
    subscribers = models.ManyToManyField(
        User,
        through='Subscription',
        related_name='subscribed_artists',
        blank=True
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Only update counts if the instance has been saved (has a pk)
        if self.pk:
            # Update artwork count
            self.artwork_count = self.artworks.count()
            # Update subscribers count
            self.subscribers_count = self.subscribers.count()
        super().save(*args, **kwargs)

    def update_artwork_count(self):
        """Update the artwork count for this artist"""
        if self.pk:
            self.artwork_count = self.artworks.count()
            self.save(update_fields=['artwork_count'])


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name='subscription_set'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'artist')
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        return f"{self.user.username} subscribed to {self.artist.name}"


class Notification(models.Model):
    ARTWORK_ADDED = 'artwork_added'
    ARTWORK_UPDATED = 'artwork_updated'
    ARTWORK_DELETED = 'artwork_deleted'
    SUBSCRIPTION = 'subscription'
    
    NOTIFICATION_TYPES = [
        (ARTWORK_ADDED, 'Artwork Added'),
        (ARTWORK_UPDATED, 'Artwork Updated'),
        (ARTWORK_DELETED, 'Artwork Deleted'),
        (SUBSCRIPTION, 'Subscription'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    content = models.TextField()
    artwork = models.ForeignKey(
        'Artwork',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='artist_notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"


class Artwork(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    image = models.ImageField(upload_to='artworks/', null=True, blank=True)
    image_url = models.URLField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    artist = models.ForeignKey(
        'Artist',
        on_delete=models.CASCADE,
        related_name='artworks'
    )

    def __str__(self):
        return self.title

    @property
    def get_image(self):
        """Return either the image file URL or the image URL"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return self.image_url or ''

    def save(self, *args, **kwargs):
        # Update artist's artwork count
        super().save(*args, **kwargs)
        self.artist.save()


@receiver(post_save, sender=Artwork)
def update_artwork_count_on_save(sender, instance, **kwargs):
    """Update the artist's artwork count when an artwork is saved"""
    instance.artist.update_artwork_count()


@receiver(post_delete, sender=Artwork)
def update_artwork_count_on_delete(sender, instance, **kwargs):
    """Update the artist's artwork count when an artwork is deleted"""
    instance.artist.update_artwork_count()


class Cart(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='cart'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('cart', 'artwork')

    def __str__(self):
        return f"{self.quantity} x {self.artwork.title} in {self.cart}"

    @property
    def total_price(self):
        return self.artwork.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='orders'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    payment_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return (
            f"{self.quantity} x {self.artwork.title} in Order {self.order.id}"
        )

    @property
    def total_price(self):
        return self.price * self.quantity
