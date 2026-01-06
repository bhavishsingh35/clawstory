from django.urls import path
from .views import login_view, signup_view,dashboard
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("signup/", signup_view, name="signup"),
    path("logout/", auth_views.LogoutView.as_view(),name="logout"),
    path(
    "forgot-password/",
    auth_views.PasswordResetView.as_view(
        template_name="accounts/forgot_password.html",
        success_url="/accounts/forgot-password/done/"
    ),
    name="forgot_password",
),
    path(
      "forgot-password/done/",
      auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"
      ),
      name="password_reset_done"
    ),
    path(
    "reset/<uidb64>/<token>/",
    auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/accounts/reset/done/"
    ),
    name="password_reset_confirm",
),
    path(
      "reset/done/",
      auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"
      ),
      name="password_reset_complete"
    ),
    path("dashboard/", dashboard, name="dashboard"),
]