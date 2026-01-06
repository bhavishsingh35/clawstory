from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignupForm, LoginForm
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from orders.models import Order
from django.db.models import Sum

# SIGNUP
from django.contrib import messages
from .forms import SignupForm

@never_cache
def signup_view(request):
     if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    
     form = SignupForm(request.POST or None)

     if request.method == "POST":
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.save()

            messages.success(request, "Account created successfully. Please login.")
            return redirect("accounts:login")
     else:
        form = SignupForm()

     return render(request, "accounts/signup.html", {"form": form})

# LOGIN
@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")   # IMPORTANT

    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user:
                login(request, user)
                return redirect("accounts:dashboard")
            else:
                messages.error(request, "Wrong username or password")

    return render(request,"accounts/login.html",{"form":form})
         

# LOGOUT
# def logout_view(request):
#     logout(request)
#     return redirect("accounts:login")

@never_cache
@login_required
def dashboard(request):
    user = request.user

    orders = Order.objects.filter(user=user).prefetch_related("items")

    total_spent = orders.aggregate(
        total=Sum("total")
    )["total"] or 0

    total_orders = orders.count()

    context = {
        "user": user,
        "orders": orders,
        "total_spent": total_spent,
        "total_orders": total_orders,
    }

    return render(request, "accounts/dashboard.html", context)