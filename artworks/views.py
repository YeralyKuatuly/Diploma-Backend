from rest_framework import generics, viewsets, status, permissions
from rest_framework.response import Response
from .models import (
    Artist, Artwork, Subscription, Notification, Cart, CartItem, Order, OrderItem
)
from .serializers import (
    ArtistSerializer, ArtworkSerializer, SubscriptionSerializer,
    NotificationSerializer, CartSerializer, OrderSerializer
)
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter
)
from rest_framework.decorators import action, api_view
from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
import os
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer, CharField, DictField


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
        data_str = str(request.data)
        print(f"Request data received: {data_str}")
        print(f"Request FILES: {request.FILES}")

        # Handle profile picture upload
        profile_picture = request.FILES.get('profile_picture') or \
            request.FILES.get('profile_image')
        if profile_picture:
            print(
                f"Processing profile picture: {profile_picture.name} "
                f"({profile_picture.content_type}, {profile_picture.size} bytes)"
            )

            # If there's an existing profile picture, delete it to avoid orphaned files
            if instance.profile_image:
                try:
                    instance.profile_image.delete(save=False)
                    print("Deleted old profile picture")
                except Exception as e:
                    print(
                        f"Error deleting old profile picture: {str(e)}"
                    )

            # Set the new profile picture
            instance.profile_image = profile_picture
            instance.save()
            print(
                f"Saved new profile picture: {instance.profile_image.url}"
            )

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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='id',
                type=int,
                location=OpenApiParameter.PATH,
                description='Notification ID'
            )
        ],
        responses={200: NotificationSerializer}
    )
    def retrieve(self, request, pk: int, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


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
        description=(
            "Create a new artwork for the authenticated artist"
        )
    )
    def create(self, request, *args, **kwargs):
        try:
            # Print request info for debugging
            print(f"User: {request.user.username}, authenticated: {request.user.is_authenticated}")
            
            try:
                artist = Artist.objects.get(user=request.user)
                print(f"Found artist profile: {artist.name} (ID: {artist.id})")
            except Artist.DoesNotExist:
                error_msg = "You must be registered as an artist to add artwork"
                print(f"Error: {error_msg}")
                return Response(
                    {"detail": error_msg},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Print debug information
            print("Request data received:", request.data)
            print("Request FILES:", request.FILES)

            # Handle image file upload
            image_file = request.FILES.get('image')
            if image_file:
                print("Processing image file:", image_file.name)
            else:
                print("No image file received")

            # Create serializer with context and data
            serializer = self.get_serializer(
                data=request.data,
                context={'request': request}
            )
            
            if not serializer.is_valid():
                print(f"Serializer errors: {serializer.errors}")
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save the artwork
            artwork = serializer.save()
            print(f"Artwork created successfully: {artwork.title} (ID: {artwork.id})")

            # Update the artist's artwork count
            artist.update_artwork_count()
            
            # Create notifications for subscribers
            self._create_notifications_for_subscribers(artist, artwork)

            return Response(
                self.get_serializer(artwork).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            print(f"Unexpected error creating artwork: {str(e)}")
            import traceback
            traceback.print_exc()
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


class DebugRequestSerializer(Serializer):
    method = CharField()
    data = DictField()
    files = DictField()
    headers = DictField()
    user = CharField()
    auth = CharField()

@api_view(['POST'])
@extend_schema(
    request=None,
    responses={200: DebugRequestSerializer}
)
def debug_request(request):
    """Debug view to check request data"""
    data = {
        'method': request.method,
        'data': request.data,
        'files': {
            k: f"{v.name} ({v.content_type}, {v.size} bytes)"
            for k, v in request.FILES.items()
        },
        'headers': {k: v for k, v in request.headers.items()},
        'user': str(request.user),
        'auth': str(request.auth),
    }
    serializer = DebugRequestSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data)


def debug_media_file(request, path):
    """Debug view to check a specific media file"""
    media_root = settings.MEDIA_ROOT
    file_path = os.path.join(media_root, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        raise Http404(f"File not found: {file_path}")


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for shopping cart operations
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_cart(self, request):
        """Helper method to get or create a cart for the current user"""
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            return cart
        except Exception as e:
            print(f"Error getting cart: {str(e)}")
            raise

    @extend_schema(
        summary="Get current user's cart",
        description="Retrieve the cart for the current user"
    )
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        cart = self.get_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Add item to cart",
        description="Add an artwork to the user's cart"
    )
    @action(detail=False, methods=['post'], url_path='add_item')
    def add_item(self, request):
        artwork_id = request.data.get('artwork_id')
        
        # Debug log to see what data is being received
        print(f"Add item request data: {request.data}")
        
        if not artwork_id:
            return Response(
                {"detail": "artwork_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert artwork_id to int if it's a string
            try:
                artwork_id = int(artwork_id)
            except (ValueError, TypeError):
                return Response(
                    {"detail": f"Invalid artwork_id format: {artwork_id}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get the artwork
            try:
                artwork = Artwork.objects.get(id=artwork_id)
            except Artwork.DoesNotExist:
                return Response(
                    {"detail": f"Artwork with ID {artwork_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if artwork is available
            if not artwork.is_available:
                return Response(
                    {"detail": "This artwork is not available for purchase"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create the cart
            cart = self.get_cart(request)
            
            # Check if item already in cart
            if CartItem.objects.filter(cart=cart, artwork=artwork).exists():
                return Response(
                    {"detail": "This artwork is already in your cart"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Always add with quantity = 1
            cart_item = CartItem.objects.create(
                cart=cart,
                artwork=artwork,
                quantity=1
            )
                
            serializer = CartSerializer(cart, context={'request': request})
            return Response(serializer.data)
            
        except Exception as e:
            print(f"Error in add_item: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Remove item from cart",
        description="Remove an artwork from the user's cart"
    )
    @action(detail=False, methods=['post'], url_path='remove_item')
    def remove_item(self, request):
        artwork_id = request.data.get('artwork_id')
        
        # Debug log
        print(f"Remove item request data: {request.data}")
        
        if not artwork_id:
            return Response(
                {"detail": "artwork_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert artwork_id to int if it's a string
            try:
                artwork_id = int(artwork_id)
            except (ValueError, TypeError):
                return Response(
                    {"detail": f"Invalid artwork_id format: {artwork_id}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get the cart
            cart = self.get_cart(request)
            
            # Find cart item
            try:
                cart_item = CartItem.objects.get(cart=cart, artwork_id=artwork_id)
                
                # Always delete the item, regardless of quantity
                cart_item.delete()
                    
                serializer = CartSerializer(cart, context={'request': request})
                return Response(serializer.data)
                
            except CartItem.DoesNotExist:
                return Response(
                    {"detail": "This item is not in your cart"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            print(f"Error in remove_item: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Clear cart",
        description="Remove all items from the user's cart"
    )
    @action(detail=False, methods=['post'], url_path='clear')
    def clear_cart(self, request):
        try:
            # Get the cart
            cart = self.get_cart(request)
            
            # Delete all items
            count = cart.items.count()
            cart.items.all().delete()
            
            print(f"Cleared {count} items from cart")
            
            serializer = CartSerializer(cart, context={'request': request})
            return Response({
                "detail": f"Successfully removed {count} items from your cart",
                "cart": serializer.data
            })
            
        except Exception as e:
            print(f"Error in clear_cart: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)],
        responses={200: SubscriptionSerializer}
    )
    def retrieve(self, request, pk: int, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="List user subscriptions",
        description="Get all artists that the current user is subscribed to"
    )
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Create subscription",
        description="Create a new subscription to an artist"
    )
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if already subscribed
        artist_id = serializer.validated_data.get('artist').id
        if Subscription.objects.filter(
            user=request.user, 
            artist_id=artist_id
        ).exists():
            return Response(
                {"detail": "You are already subscribed to this artist"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="Delete subscription",
        description="Unsubscribe from an artist"
    )
    def destroy(self, request, pk=None):
        instance = self.get_object()
        
        # Ensure user can only delete their own subscriptions
        if instance.user != request.user:
            return Response(
                {"detail": "You do not have permission to delete this subscription"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        self.perform_destroy(instance)
        return Response(
            {"detail": "Successfully unsubscribed"},
            status=status.HTTP_204_NO_CONTENT
        )


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)],
        responses={200: OrderSerializer}
    )
    def retrieve(self, request, pk: int, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="List user orders",
        description="Get all orders for the current user"
    )
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Create an order",
        description="Create a new order from the items in the user's cart"
    )
    def create(self, request):
        try:
            # Get the cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Check if cart is empty
            if not cart.items.exists():
                return Response(
                    {"detail": "Your cart is empty"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get shipping address from request
            shipping_address = request.data.get('shipping_address')
            if not shipping_address:
                return Response(
                    {"detail": "Shipping address is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate total amount
            total_amount = sum(item.total_price for item in cart.items.all())
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                total_amount=total_amount
            )
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    artwork=cart_item.artwork,
                    price=cart_item.artwork.price,
                    quantity=cart_item.quantity
                )
            
            # Clear the cart
            cart.items.all().delete()
            
            serializer = self.get_serializer(order)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            print(f"Error creating order: {str(e)}")
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Cancel an order",
        description="Cancel a pending order"
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        try:
            order = self.get_object()
            
            # Check if order can be cancelled
            if order.status != 'pending':
                return Response(
                    {"detail": f"Cannot cancel order in {order.status} status"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update order status
            order.status = 'cancelled'
            order.save()
            
            serializer = self.get_serializer(order)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
