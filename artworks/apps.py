from django.apps import AppConfig


class ArtworksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artworks'

    def ready(self):
        # noqa: F401
        import artworks.signals  # This import is needed to register signals
