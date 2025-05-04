from django.urls import path
from .views import (
    RegisterView,
    LogoutView,
    ProfileView,
    DeleteAccountView,
    SubscriptionsView,
    RateLimitedTokenObtainPairView,
    RateLimitedTokenRefreshView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', RateLimitedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', RateLimitedTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('subscriptions/', SubscriptionsView.as_view(), name='user-subscriptions'),
    path('delete/', DeleteAccountView.as_view(), name='delete-account'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
