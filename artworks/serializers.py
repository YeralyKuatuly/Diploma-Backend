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
                'bio': 'A talented artist from New York',
                'profile_picture': 'http://example.com/profile.jpg'
            }
        )
    ]
)
class ArtistSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = Artist
        fields = [
            'id', 'name', 'bio', 'profile_picture',
            'user', 'username', 'email'
        ]

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
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(),
        source='artist',
        write_only=True
    )
    image = serializers.SerializerMethodField()

    class Meta:
        model = Artwork
        fields = [
            'id', 'title', 'description',
            'image', 'price', 'artist', 'artist_id'
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image_file and request:
            return request.build_absolute_uri(obj.image_file.url)
        return obj.image_url

    def create(self, validated_data):
        image_file = self.context['request'].FILES.get('image_file')
        image_url = self.context['request'].data.get('image_url')
        
        if image_file:
            validated_data['image_file'] = image_file
        elif image_url:
            validated_data['image_url'] = image_url
            
        return Artwork.objects.create(**validated_data)
