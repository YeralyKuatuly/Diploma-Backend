from django.contrib.auth.models import User
from rest_framework import serializers
from artworks.models import Artist
from django.db import transaction


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True,
                                     style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        """Override create method to hash passwords properly"""
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)
    artist_name = serializers.CharField(required=False)  # Optional artist name
    bio = serializers.CharField(required=False)  # Optional artist bio

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
