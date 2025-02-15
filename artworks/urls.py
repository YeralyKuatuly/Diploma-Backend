from django.urls import path
from .views import (
    ArtistListCreateView,
    ArtworkListCreateView,
    ArtworkDetailView,
    ArtistDetailView,
)


urlpatterns = [
    # Artist endpoints
    path('artists/', ArtistListCreateView.as_view(), name='artist-list'),
    path('artists/<int:pk>/', ArtistDetailView.as_view(),
         name='artist-detail'),

    # Artwork endpoints
    path('artworks/', ArtworkListCreateView.as_view(), name='artwork-list'),
    path('artworks/<int:pk>/', ArtworkDetailView.as_view(),
         name='artwork-detail'),
]
