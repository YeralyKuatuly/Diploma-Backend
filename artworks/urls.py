from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ArtistViewSet, ArtworkViewSet, SubscriptionViewSet,
    NotificationViewSet, CartViewSet, OrderViewSet, debug_media, debug_request, debug_media_file
)

router = DefaultRouter()
router.register(r'artists', ArtistViewSet)
router.register(r'artworks', ArtworkViewSet)
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path('debug-media/', debug_media, name='debug-media'),
    path('debug-request/', debug_request, name='debug-request'),
    path('debug-media-file/<path:path>', debug_media_file, name='debug-media-file'),
]
