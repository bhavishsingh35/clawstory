from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.contrib.auth.views import PasswordResetView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from .forms import SignupForm, LoginForm
from orders.models import Order


# ==================================================
# SIGNUP
# ==================================================
@never_cache
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = SignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()  # form handles normalization safely

        messages.success(
            request,
            "Account created successfully. Please login."
        )
        return redirect("accounts:login")

    return render(
        request,
        "accounts/signup.html",
        {"form": form},
    )


# ==================================================
# LOGIN (SAFE REDIRECT + SINGLE SOURCE AUTH)
# ==================================================
@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = LoginForm(request.POST or None)
    next_url = request.GET.get("next")

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)

        # Safe redirect (prevents open redirect attacks)
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)

        return redirect("accounts:dashboard")

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "next": next_url,
        },
    )


# ==================================================
# LOGOUT (CSRF SAFE)
# ==================================================
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("pages:home")


# ==================================================
# DASHBOARD (PAID ORDERS ONLY)
# ==================================================
@never_cache
@login_required
def dashboard(request):
    user = request.user

    orders = (
        Order.objects
        .filter(
            user=user,
            status=Order.PAID,  # ✅ FIXED
        )
        .prefetch_related("items")
        .order_by("-created_at")
    )

    aggregates = orders.aggregate(
        total_spent=Sum("total_amount"),
    )

    context = {
        "user": user,
        "orders": orders,
        "total_spent": aggregates["total_spent"] or 0,
        "total_orders": orders.count(),
    }

    return render(
        request,
        "accounts/dashboard.html",
        context,
    )


class HTMLPasswordResetView(PasswordResetView):
    template_name = "accounts/forgot_password.html"
    email_template_name = "accounts/password_reset_email.html"
    html_email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"