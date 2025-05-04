from django.contrib.auth.models import User
from rest_framework import serializers
from artworks.models import Artist
from django.db import transaction
from drf_spectacular.utils import extend_schema_field


class UserSerializer(serializers.ModelSerializer):
    artist = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'artist']
        read_only_fields = ['id']
    
    def get_artist(self, obj):
        try:
            artist = Artist.objects.get(user=obj)
            return {
                'id': artist.id,
                'name': artist.name,
                'bio': artist.bio,
                'profile_picture': self.get_profile_picture_url(artist),
                'telegram': artist.telegram,
                'whatsapp': artist.whatsapp,
                'contact_email': artist.contact_email,
                'kaspi_phone': artist.kaspi_phone,
                'kaspi_card_number': artist.kaspi_card_number
            }
        except Artist.DoesNotExist:
            return None
    
    def get_profile_picture_url(self, artist):
        if artist.profile_image and hasattr(artist.profile_image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(artist.profile_image.url)
            return artist.profile_image.url
        return None


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)
    artist_name = serializers.CharField(required=False)
    bio = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'artist_name', 'bio')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken")
        return value

    @transaction.atomic
    def create(self, validated_data):
        artist_name = validated_data.pop('artist_name', None)
        bio = validated_data.pop('bio', None)

        # Create User
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # Update or create Artist profile
        Artist.objects.filter(user=user).update(
            name=artist_name or user.username,
            bio=bio or ""
        )

        return user
