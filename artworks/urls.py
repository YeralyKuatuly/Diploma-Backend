from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArtistViewSet, ArtworkViewSet, debug_media, debug_request, debug_media_file

router = DefaultRouter()
router.register(r'artists', ArtistViewSet)
router.register(r'artworks', ArtworkViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('debug-media/', debug_media, name='debug-media'),
    path('debug-request/', debug_request, name='debug-request'),
    path('debug-media-file/<path:path>', debug_media_file, name='debug-media-file'),
]
