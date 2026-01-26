from django.urls import path
from .views import HTMLPasswordResetView
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy


from .views import (
    login_view,
    signup_view,
    logout_view,
    dashboard,
)

app_name = "accounts"

urlpatterns = [

    # ==================================================
    # AUTH
    # ==================================================
    path("login/", login_view, name="login"),
    path("signup/", signup_view, name="signup"),
    path("logout/", logout_view, name="logout"),

    # ==================================================
    # PASSWORD RESET FLOW (SECURE & REVERSIBLE)
    # ==================================================
    path(
        "forgot-password/",
        HTMLPasswordResetView.as_view(
            template_name="accounts/forgot_password.html",
            success_url="/accounts/forgot-password/done/",
        ),
        name="forgot_password",
    ),

    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # ==================================================
    # USER DASHBOARD
    # ==================================================
    path("dashboard/", dashboard, name="dashboard"),
]
