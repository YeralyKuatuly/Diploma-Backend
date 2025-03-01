from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView)
from rest_framework import generics, status
from django.contrib.auth.models import User
from .serializers import UserSerializer, RegisterSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from artworks.models import Artist
from artworks.serializers import ArtistSerializer


class RegisterView(APIView):
    serializer_class = RegisterSerializer

    @extend_schema(
        summary="Register new user",
        description="Register a new user and create their artist profile"
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Registration successful",
                "username": user.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get user profile",
        description="Get the current user's profile information including their artist profile"
    )
    def get(self, request):
        user = request.user
        try:
            artist = Artist.objects.get(user=user)
            artist_data = ArtistSerializer(artist, context={'request': request}).data
            
            return Response({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'artist': artist_data
            })
        except Artist.DoesNotExist:
            return Response({
                'error': 'Artist profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
