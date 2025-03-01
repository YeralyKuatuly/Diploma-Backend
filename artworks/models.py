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

    def __str__(self):
        return self.name

    def update_artwork_count(self):
        """Update the artwork count for this artist"""
        self.artwork_count = self.artworks.count()
        self.save(update_fields=['artwork_count'])


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
