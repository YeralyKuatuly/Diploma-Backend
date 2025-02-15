from rest_framework import generics
from .models import Artist, Artwork
from .serializers import ArtistSerializer, ArtworkSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    tags=['Artists'],
    description='List all artists or create a new artist'
)
class ArtistListCreateView(generics.ListCreateAPIView):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer

    @extend_schema(
        summary='List all artists',
        description='Returns a list of all artists in the gallery'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Create a new artist',
        description='Create a new artist profile'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    tags=['Artists'],
    description='Retrieve, update or delete an artist'
)
class ArtistDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer

    @extend_schema(
        summary='Get artist details',
        description='Returns the details of a specific artist'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Update artist',
        description='Update the details of a specific artist'
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='Delete artist',
        description='Delete a specific artist'
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


@extend_schema(
    tags=['Artworks'],
    description='List all artworks or create a new artwork'
)
class ArtworkListCreateView(generics.ListCreateAPIView):
    queryset = Artwork.objects.all()
    serializer_class = ArtworkSerializer

    @extend_schema(
        summary='List all artworks',
        description='Returns a list of all artworks in the gallery'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Create a new artwork',
        description='Create a new artwork with the provided data'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ArtworkListView(generics.ListAPIView):
    queryset = Artwork.objects.all()
    serializer_class = ArtworkSerializer


@extend_schema(
    tags=['Artworks'],
    description='Retrieve, update or delete an artwork'
)
class ArtworkDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Artwork.objects.all()
    serializer_class = ArtworkSerializer

    @extend_schema(
        summary='Get artwork details',
        description='Returns the details of a specific artwork'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Update artwork',
        description='Update the details of a specific artwork'
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='Delete artwork',
        description='Delete a specific artwork'
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
