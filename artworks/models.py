from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class Artist(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='artist'
    )
    name = models.CharField(max_length=255)  # Artist's display name
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to="artists/",
        null=True,
        blank=True
    )
    artwork_count = models.IntegerField(default=0)
    subscribers = models.ManyToManyField(
        User,
        through='Subscription',
        related_name='subscribed_artists',
        blank=True
    )

    def __str__(self):
        return self.name

    def update_artwork_count(self):
        """Update the artwork count for this artist"""
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
        related_name='artist_subscribers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'artist')
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        return f"{self.user.username} subscribed to {self.artist.name}"


class Notification(models.Model):
    ARTWORK_ADDED = 'artwork_added'
    
    NOTIFICATION_TYPES = [
        (ARTWORK_ADDED, 'New Artwork Added'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES
    )
    content = models.CharField(max_length=255)
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
        related_name='artist_notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.content}"


class Artwork(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image_file = models.ImageField(
        upload_to='artworks/',
        null=True,
        blank=True
    )
    image_url = models.URLField(null=True, blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name='artworks'
    )

    def __str__(self):
        return self.title

    @property
    def image(self):
        """Return either the image URL or the file URL"""
        if self.image_file:
            return self.image_file.url
        return self.image_url


@receiver(post_save, sender=Artwork)
def update_artwork_count_on_save(sender, instance, **kwargs):
    """Update the artist's artwork count when an artwork is saved"""
    instance.artist.update_artwork_count()


@receiver(post_delete, sender=Artwork)
def update_artwork_count_on_delete(sender, instance, **kwargs):
    """Update the artist's artwork count when an artwork is deleted"""
    instance.artist.update_artwork_count()
