from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError


# ==================================================
# SIGNUP FORM (PRODUCTION SAFE)
# ==================================================
class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        if not email:
            raise ValidationError("Email address is required.")

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "An account with this email already exists."
            )

        return email

    def save(self, commit=True):
        """
        Override save to ensure email normalization
        and future extensibility.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()

        if commit:
            user.save()

        return user


# ==================================================
# LOGIN FORM (USERNAME OR EMAIL READY)
# ==================================================
class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username or Email",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": "Username or Email",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username", "").strip()
        password = cleaned_data.get("password")

        if not username or not password:
            raise ValidationError("Both fields are required.")

        # Try username first, then email
        user = authenticate(
            username=username,
            password=password,
        )

        if user is None:
            try:
                user_obj = User.objects.get(email__iexact=username)
                user = authenticate(
                    username=user_obj.username,
                    password=password,
                )
            except User.DoesNotExist:
                user = None

        if user is None:
            raise ValidationError(
                "Invalid login credentials."
            )

        if not user.is_active:
            raise ValidationError(
                "This account is inactive. Contact support."
            )

        self.user = user
        return cleaned_data

    def get_user(self):
        return getattr(self, "user", None)
