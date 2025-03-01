from rest_framework import serializers
from .models import Artist, Artwork
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

    class Meta:
        model = Artist
        fields = [
            'id', 'name', 'bio', 'profile_picture',
            'user', 'username', 'email', 'artwork_count'
        ]

    def get_artwork_count(self, obj):
        return obj.artworks.count()

    def get_profile_picture(self, obj):
        """
        Get the full URL for the profile picture.
        Debug the URL generation process.
        """
        if not obj.profile_picture:
            print(f"No profile picture for artist {obj.id}")
            return None
        
        if not hasattr(obj.profile_picture, 'url'):
            print(f"Profile picture has no URL attribute: {obj.profile_picture}")
            return None
        
        # Get the relative URL
        relative_url = obj.profile_picture.url
        print(f"Relative URL: {relative_url}")
        
        # Build absolute URL if request is available
        request = self.context.get('request')
        if not request:
            print(f"No request in context, returning relative URL: {relative_url}")
            return relative_url
        
        # Build the absolute URL
        absolute_url = request.build_absolute_uri(relative_url)
        print(f"Built absolute URL: {absolute_url}")
        return absolute_url

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
