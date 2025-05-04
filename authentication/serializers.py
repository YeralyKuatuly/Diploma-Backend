from django.contrib.auth.models import User
from rest_framework import serializers
from artworks.models import Artist
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


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


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Validate that the email exists"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "No user is registered with this email address"
            )
        return value
    
    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create reset URL (to be used in the frontend)
        request = self.context.get('request')
        domain = request.get_host() if request else settings.ALLOWED_HOSTS[0]
        protocol = 'https' if request and request.is_secure() else 'http'
        reset_url = f"{protocol}://{domain}/reset-password/{uid}/{token}/"
        
        # Prepare email
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'Art Gallery',
        }
        
        # Render email templates
        html_message = render_to_string(
            'authentication/password_reset_email.html',
            context
        )
        text_message = render_to_string(
            'authentication/password_reset_email.txt',
            context
        )
        
        email_subject = "Reset your password"
        
        # Send email
        send_mail(
            subject=email_subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        return {"success": True}


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming a password reset
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True)
    
    def validate(self, data):
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        
        try:
            uid = force_str(urlsafe_base64_decode(data['uidb64']))
            self.user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError({'uidb64': 'Invalid user ID'})
            
        if not default_token_generator.check_token(self.user, data['token']):
            raise serializers.ValidationError({'token': 'Invalid or expired token'})
            
        return data
        
    def save(self):
        self.user.set_password(self.validated_data['password'])
        self.user.save()
        return {"success": True}


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
