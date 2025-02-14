from django.urls import path
from .views import ArtistListCreateView, ArtworkListCreateView


urlpatterns = [
    path('artists/', ArtistListCreateView.as_view(), name='artists'),
    path('artworks/', ArtworkListCreateView.as_view(), name='artworks'),
]
