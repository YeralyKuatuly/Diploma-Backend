from rest_framework import generics, viewsets, status, permissions
from rest_framework.response import Response
from .models import Artist, Artwork, Subscription, Notification
from .serializers import ArtistSerializer, ArtworkSerializer, SubscriptionSerializer, NotificationSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action, api_view
from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
import os
from rest_framework.permissions import IsAuthenticated


@extend_schema(
    tags=['Artists'],
    description='List all artists or create a new artist'
)
class ArtistListCreateView(generics.ListCreateAPIView):
    queryset = Artist.objects.all().order_by('name')  # Order by name alphabetically
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

    @extend_schema(
        summary="Subscribe to an artist",
        description="Subscribe to receive notifications when this artist adds new artwork"
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        artist = self.get_object()
        user = request.user
        
        # Prevent subscribing to your own artist profile
        if hasattr(user, 'artist') and user.artist == artist:
            return Response(
                {"detail": "You cannot subscribe to your own artist profile"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already subscribed
        if Subscription.objects.filter(user=user, artist=artist).exists():
            return Response(
                {"detail": "You are already subscribed to this artist"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create subscription
        subscription = Subscription.objects.create(user=user, artist=artist)
        serializer = SubscriptionSerializer(
            subscription, context={'request': request}
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="Unsubscribe from an artist",
        description="Unsubscribe from receiving notifications from this artist"
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unsubscribe(self, request, pk=None):
        artist = self.get_object()
        user = request.user
        
        try:
            subscription = Subscription.objects.get(user=user, artist=artist)
            subscription.delete()
            return Response(
                {"detail": "You have unsubscribed from this artist"}, 
                status=status.HTTP_200_OK
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "You are not subscribed to this artist"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user)
    
    @extend_schema(
        summary="Mark notification as read",
        description="Mark a specific notification as read"
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        
        return Response(
            {"detail": "Notification marked as read"},
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        summary="Mark all notifications as read",
        description="Mark all of the user's notifications as read"
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        notifications = self.get_queryset()
        notifications.update(is_read=True)
        
        return Response(
            {"detail": "All notifications marked as read"},
            status=status.HTTP_200_OK
        )


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

    @extend_schema(
        summary="Create a new artwork",
        description="Create a new artwork for the authenticated artist"
    )
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
            
            # Create notifications for subscribers
            self._create_notifications_for_subscribers(artist, artwork)

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

    def _create_notifications_for_subscribers(self, artist, artwork):
        """Create notifications for all subscribers when new artwork is added"""
        subscriptions = Subscription.objects.filter(artist=artist)
        
        for subscription in subscriptions:
            Notification.objects.create(
                user=subscription.user,
                notification_type=Notification.ARTWORK_ADDED,
                content=f"{artist.name} added new artwork: {artwork.title}",
                artwork=artwork,
                artist=artist
            )

    @extend_schema(
        summary="Update an artwork",
        description="Update an existing artwork's details"
    )
    def update(self, request, *args, **kwargs):
        """
        Update an artwork with better error handling
        """
        instance = self.get_object()

        # Check if user is the owner of this artwork
        if instance.artist.user != request.user:
            return Response(
                {"detail": "You do not have permission to update this artwork."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(
            instance, 
            data=request.data, 
            partial=kwargs.get('partial', False),
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @extend_schema(
        summary="Delete an artwork",
        description="Delete an existing artwork"
    )
    def destroy(self, request, *args, **kwargs):
        """
        Delete an artwork with better error handling
        """
        instance = self.get_object()

        # Check if user is the owner of this artwork
        if instance.artist.user != request.user:
            return Response(
                {"detail": "You do not have permission to delete this artwork."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete the artwork
        self.perform_destroy(instance)

        # Update the artist's artwork count
        instance.artist.update_artwork_count()

        return Response(
            {"detail": "Artwork successfully deleted."},
            status=status.HTTP_204_NO_CONTENT
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


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
