from rest_framework import generics, viewsets, status, permissions
from rest_framework.response import Response
from .models import Artist, Artwork
from .serializers import ArtistSerializer, ArtworkSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action, api_view
from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
import os


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


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'artist'):
            return obj.artist.user == request.user
        return False


class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @extend_schema(
        summary="Get artist details with artworks",
        description="Retrieve an artist's profile with their artworks"
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Get artist's artworks
        artworks = Artwork.objects.filter(artist=instance)
        artwork_serializer = ArtworkSerializer(
            artworks, many=True, context={'request': request}
        )

        data = serializer.data
        data['artworks'] = artwork_serializer.data

        # Update artwork count
        instance.update_artwork_count()

        return Response(data)

    @extend_schema(
        summary="Update artist profile",
        description="Update the artist's profile information"
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if user is the owner of this artist profile
        if instance.user != request.user:
            return Response(
                {"detail": "You do not have permission to update this profile."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Print debug information
        print(f"Request data: {request.data}")
        print(f"Request FILES: {request.FILES}")
        
        # Handle profile picture upload
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            print(f"Processing profile picture: {profile_picture.name} ({profile_picture.content_type}, {profile_picture.size} bytes)")
            
            # If there's an existing profile picture, delete it to avoid orphaned files
            if instance.profile_picture:
                try:
                    instance.profile_picture.delete(save=False)
                    print(f"Deleted old profile picture")
                except Exception as e:
                    print(f"Error deleting old profile picture: {str(e)}")
            
            # Set the new profile picture
            instance.profile_picture = profile_picture
            instance.save()
            print(f"Saved new profile picture: {instance.profile_picture.url}")
        
        serializer = self.get_serializer(
            instance, 
            data=request.data, 
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return the updated instance with the full URL for profile_picture
        updated_serializer = self.get_serializer(instance, context={'request': request})
        return Response(updated_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class ArtworkViewSet(viewsets.ModelViewSet):
    queryset = Artwork.objects.all()
    serializer_class = ArtworkSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def create(self, request, *args, **kwargs):
        """
        Create a new artwork with better error handling
        """
        # Print debug information
        print(f"Request data: {request.data}")
        print(f"Request FILES: {request.FILES}")

        # Check if artist_id is provided
        artist_id = request.data.get('artist_id')
        if not artist_id:
            return Response(
                {"detail": "artist_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the artist
            artist = Artist.objects.get(id=artist_id)

            # Check if the user is the owner of this artist profile
            if artist.user != request.user:
                return Response(
                    {"detail": "You can only create artworks for your own artist profile."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Create serializer with context
            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)

            # Save the artwork
            artwork = serializer.save(artist=artist)

            # Update the artist's artwork count
            artist.update_artwork_count()

            # Return the created artwork
            return Response(
                self.get_serializer(artwork, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        except Artist.DoesNotExist:
            return Response(
                {"detail": f"Artist with ID {artist_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error creating artwork: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


def debug_media(request):
    """Debug view to check media configuration"""
    media_root = settings.MEDIA_ROOT
    media_url = settings.MEDIA_URL

    # Check if MEDIA_ROOT exists
    media_root_exists = os.path.exists(media_root)

    # List files in MEDIA_ROOT
    files = []
    if media_root_exists:
        for root, dirs, filenames in os.walk(media_root):
            for filename in filenames:
                files.append(os.path.join(root, filename).replace(media_root, ''))

    response = f"""
    <h1>Media Debug Info</h1>
    <p>MEDIA_URL: {media_url}</p>
    <p>MEDIA_ROOT: {media_root}</p>
    <p>MEDIA_ROOT exists: {media_root_exists}</p>

    <h2>Files in MEDIA_ROOT:</h2>
    <ul>
    {"".join(f"<li>{f} - <a href='{media_url}{f.lstrip('/')}'>Link</a></li>" for f in files)}
    </ul>
    """

    return HttpResponse(response)


@api_view(['POST'])
def debug_request(request):
    """Debug view to check request data"""
    data = {
        'method': request.method,
        'data': request.data,
        'files': {k: f"{v.name} ({v.content_type}, {v.size} bytes)" for k, v in request.FILES.items()},
        'headers': {k: v for k, v in request.headers.items()},
        'user': str(request.user),
        'auth': str(request.auth),
    }
    return Response(data)


def debug_media_file(request, path):
    """Debug view to check a specific media file"""
    media_root = settings.MEDIA_ROOT
    file_path = os.path.join(media_root, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        raise Http404(f"File not found: {file_path}")
