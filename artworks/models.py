from django.db import models
from django.contrib.auth.models import User


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

    def __str__(self):
        return self.name


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
