from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView)
from rest_framework import generics, status
from django.contrib.auth.models import User
from .serializers import UserSerializer, RegisterSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from artworks.models import Artist, Subscription
from artworks.serializers import ArtistSerializer, ArtistDetailSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from rest_framework_simplejwt.exceptions import TokenError
from django.db import transaction
from rest_framework.decorators import action
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator


class RateLimitedTokenObtainPairView(TokenObtainPairView):
    @method_decorator(ratelimit(key='ip', rate='5/m', method=['POST']))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RateLimitedTokenRefreshView(TokenRefreshView):
    @method_decorator(ratelimit(key='ip', rate='5/m', method=['POST']))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RegisterView(APIView):
    serializer_class = RegisterSerializer

    @extend_schema(
        summary="Register new user",
        description="Register a new user and create their artist profile"
    )
    @method_decorator(ratelimit(key='ip', rate='3/h', method=['POST']))
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
    @method_decorator(ratelimit(key='ip', rate='5/m', method=['POST']))
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
    @method_decorator(ratelimit(key='ip', rate='30/m', method=['GET']))
    def get(self, request):
        user = request.user
        try:
            artist = Artist.objects.get(user=user)
            artist_data = ArtistSerializer(
                artist, context={'request': request}
            ).data
            
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


class SubscriptionsView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get user subscriptions",
        description="Get the list of artists the user is subscribed to"
    )
    @method_decorator(ratelimit(key='ip', rate='30/m', method=['GET']))
    def get(self, request):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user)
        
        # Get the artist objects from subscriptions
        subscribed_artists = [sub.artist for sub in subscriptions]
        
        # Serialize the artists with detail information
        serializer = ArtistDetailSerializer(
            subscribed_artists, many=True, context={'request': request}
        )
        
        return Response(serializer.data)


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete user account",
        description="Delete the current user's account and all associated data"
    )
    @method_decorator(ratelimit(key='ip', rate='3/h', method=['DELETE']))
    @transaction.atomic
    def delete(self, request):
        try:
            # Get the user ID from the URL if provided, otherwise use request.user
            user_id = request.data.get('user_id')
            target_user = User.objects.get(id=user_id) if user_id else request.user
            
            # Check if user is trying to delete their own account
            if target_user != request.user:
                return Response(
                    {"error": "You can only delete your own account"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Delete associated artist profile if it exists
            try:
                artist = Artist.objects.get(user=target_user)
                artist.delete()
            except Artist.DoesNotExist:
                pass
            
            # Delete the user
            target_user.delete()
            
            return Response(
                {"message": "Account successfully deleted"},
                status=status.HTTP_204_NO_CONTENT
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
