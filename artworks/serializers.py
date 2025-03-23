from rest_framework import serializers
from .models import Artist, Artwork, Subscription, Notification
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


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

    class Meta:
        model = Artist
        fields = [
            'id', 'name', 'bio', 'profile_picture',
            'user', 'username', 'email', 'artwork_count', 'is_subscribed'
        ]

    def get_artwork_count(self, obj):
        return obj.artworks.count()

    def get_profile_picture(self, obj):
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_is_subscribed(self, obj):
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
            if hasattr(request.user, 'artist'):
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
                if hasattr(user, 'artist'):
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


class ArtistDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Artist model including artwork count
    Used for subscription lists and artist details
    """
    artwork_count = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Artist
        fields = ['id', 'name', 'bio', 'profile_picture', 'artwork_count']
    
    def get_artwork_count(self, obj):
        return obj.artworks.count()
    
    def get_profile_picture(self, obj):
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(
                    obj.profile_picture.url
                )
            return obj.profile_picture.url
        return None


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
    image = serializers.SerializerMethodField()

    class Meta:
        model = Artwork
        fields = [
            'id', 'title', 'description',
            'image', 'price', 'artist', 'artist_id'
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image_file and hasattr(obj.image_file, 'url'):
            if request:
                return request.build_absolute_uri(obj.image_file.url)
            return obj.image_file.url
        return obj.image_url

    def create(self, validated_data):
        # Remove artist_id from validated_data if present
        validated_data.pop('artist_id', None)

        # Get image file or URL from request
        request = self.context.get('request')
        if request:
            image_file = request.FILES.get('image_file')
            image_url = request.data.get('image_url')

            if image_file:
                validated_data['image_file'] = image_file
            elif image_url:
                validated_data['image_url'] = image_url

        return super().create(validated_data)


class SubscriptionSerializer(serializers.ModelSerializer):
    artist_name = serializers.ReadOnlyField(source='artist.name')
    artist_profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = ['id', 'artist', 'artist_name', 'artist_profile_picture', 'created_at']
        read_only_fields = ['created_at']
    
    def get_artist_profile_picture(self, obj):
        if obj.artist.profile_picture and hasattr(obj.artist.profile_picture, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.artist.profile_picture.url)
            return obj.artist.profile_picture.url
        return None


class NotificationSerializer(serializers.ModelSerializer):
    artist_name = serializers.ReadOnlyField(source='artist.name')
    artwork_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'content', 'artist', 'artist_name',
            'artwork', 'artwork_title', 'created_at', 'is_read'
        ]
        read_only_fields = ['created_at']
    
    def get_artwork_title(self, obj):
        if obj.artwork:
            return obj.artwork.title
        return None
