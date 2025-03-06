from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView)
from rest_framework import generics, status
from django.contrib.auth.models import User
from .serializers import UserSerializer, RegisterSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from artworks.models import Artist, Artwork
from artworks.serializers import ArtistSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from rest_framework_simplejwt.exceptions import TokenError
from django.db import transaction


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


class LogoutView(APIView):
    permission_classes = []  # Allow any access

    @extend_schema(
        summary="Logout user",
        description="Blacklist the refresh token"
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get token and blacklist it
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except TokenError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


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


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete user account",
        description="Delete the current user's account and all associated data"
    )
    @transaction.atomic
    def delete(self, request):
        try:
            user = request.user
            
            # Delete associated artist profile if it exists
            try:
                artist = Artist.objects.get(user=user)
                artist.delete()
            except Artist.DoesNotExist:
                pass
            
            # Delete the user
            user.delete()
            
            return Response(
                {"message": "Account successfully deleted"},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
