from django.db import models


class Artist(models.Model):
    name = models.CharField(max_length=255)
    bio = models.TextField()
    profile_picture = models.ImageField(upload_to="artists/")

    def __str__(self):
        return self.name


class Artwork(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to="artworks/")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE,
                               related_name="artworks")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
