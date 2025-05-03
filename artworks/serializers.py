from rest_framework import serializers
from .models import Artist, Artwork, Subscription, Notification, Cart, CartItem, Order, OrderItem
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample, extend_schema_field
from authentication.serializers import UserSerializer


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Valid artist example',
            value={
                'name': 'John Doe',
                'bio': 'A passionate artist from New York',
                'profile_picture': None
            }
        )
    ]
)
class ArtistSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    artwork_count = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    @extend_schema_field(serializers.URLField)
    def get_profile_picture(self, obj) -> str:
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None

    @extend_schema_field(serializers.IntegerField)
    def get_artwork_count(self, obj) -> int:
        return obj.artworks.count()

    @extend_schema_field(serializers.BooleanField)
    def get_is_subscribed(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                artist=obj
            ).exists()
        return False

    def create(self, validated_data):
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            # If user is authenticated, use the authenticated user
            if hasattr(request.user, 'artist_profile'):
                raise serializers.ValidationError(
                    "You already have an artist profile"
                )
            validated_data['user'] = request.user
        else:
            # Handle unauthenticated user case
            username = validated_data.pop('username', None)
            email = validated_data.pop('email', None)

            if not (username and email):
                raise serializers.ValidationError(
                    "Username and email are required for new artists"
                )

            try:
                user = User.objects.get(username=username)
                if hasattr(user, 'artist_profile'):
                    raise serializers.ValidationError(
                        "This user already has an artist profile"
                    )
                validated_data['user'] = user
            except User.DoesNotExist:
                user = User.objects.create(
                    username=username,
                    email=email
                )
                validated_data['user'] = user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Remove username and email from update operation
        validated_data.pop('username', None)
        validated_data.pop('email', None)
        return super().update(instance, validated_data)

    class Meta:
        model = Artist
        fields = [
            'id', 'name', 'bio', 'profile_picture',
            'user', 'username', 'email', 'artwork_count', 'is_subscribed',
            'telegram', 'whatsapp', 'contact_email'
        ]


class ArtistDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Artist model including artwork count
    Used for subscription lists and artist details
    """
    artwork_count = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    artworks = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    
    class Meta:
        model = Artist
        fields = ['id', 'name', 'bio', 'profile_picture', 'artwork_count', 'artworks', 'is_subscribed',
                 'telegram', 'whatsapp', 'contact_email']
    
    def get_artwork_count(self, obj):
        return obj.artworks.count()
    
    def get_profile_picture(self, obj):
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(
                    obj.profile_image.url
                )
            return obj.profile_image.url
        return None

    def get_artworks(self, obj):
        artworks = obj.artworks.all()
        return ArtworkSerializer(artworks, many=True, context=self.context).data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.subscribers.filter(id=request.user.id).exists()
        return False


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Valid artwork example',
            value={
                'title': 'Sunset',
                'description': 'A beautiful sunset painting',
                'price': '299.99',
                'image_url': 'http://example.com/sunset.jpg'
            }
        )
    ]
)
class ArtworkSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer(read_only=True)
    artist_id = serializers.IntegerField(write_only=True, required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    image_url = serializers.URLField(required=False, allow_null=True)

    def get_image(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.image_url if obj.image_url else None

    class Meta:
        model = Artwork
        fields = [
            'id', 'title', 'description', 'price',
            'image', 'image_url', 'artist', 'artist_id',
            'is_available', 'created_at'
        ]
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True},
            'image_url': {'required': False, 'allow_null': True},
            'artist_id': {'required': False},
        }

    def validate(self, data):
        # Remove artist from input data if present (but keep artist_id if it exists)
        data.pop('artist', None)
        
        # Clean up empty image data
        if 'image' in data and not data['image']:
            data.pop('image')
        if 'image_url' in data and not data['image_url']:
            data.pop('image_url')
            
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("You must be authenticated to add artwork.")
            
        if not hasattr(request.user, 'artist_profile'):
            raise serializers.ValidationError("You must be registered as an artist to add artwork.")
            
        # Pop artist_id if it exists, we'll use the current user's artist
        validated_data.pop('artist_id', None)
        
        artist = request.user.artist_profile
        return Artwork.objects.create(artist=artist, **validated_data)


class SubscriptionSerializer(serializers.ModelSerializer):
    artist_name = serializers.ReadOnlyField(source='artist.name')
    artist_profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = ['id', 'artist', 'artist_name', 'artist_profile_picture', 'created_at']
        read_only_fields = ['created_at']
    
    def get_artist_profile_picture(self, obj):
        if obj.artist.profile_image and hasattr(obj.artist.profile_image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.artist.profile_image.url)
            return obj.artist.profile_image.url
        return None


class NotificationSerializer(serializers.ModelSerializer):
    artist_name = serializers.ReadOnlyField(source='artist.name')
    artwork_title = serializers.SerializerMethodField()
    artwork = ArtworkSerializer(read_only=True)
    artist = ArtistSerializer(read_only=True)
    
    @extend_schema_field(serializers.CharField)
    def get_artwork_title(self, obj) -> str:
        if obj.artwork:
            return obj.artwork.title
        return None

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'content', 'artist', 'artist_name',
            'artwork', 'artwork_title', 'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']


class CartItemSerializer(serializers.ModelSerializer):
    artwork = ArtworkSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'artwork', 'quantity', 'total_price', 'added_at']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    artwork = ArtworkSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'artwork', 'price', 'quantity', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'total_amount', 'shipping_address', 'payment_id', 'items', 'created_at', 'updated_at']
        read_only_fields = ['status', 'payment_id']
