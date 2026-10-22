from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path("", lambda request: redirect("dashboard"), name="home"),
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="login.html", authentication_form=LoginForm, redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),  # POST only
    path("dashboard/", views.dashboard, name="dashboard"),
    path("generate/", views.generate_email, name="generate_email"),
    path("emails/", views.email_history, name="email_history"),
    path("emails/<int:pk>/result/", views.email_result, name="email_result"),
    path("emails/<int:pk>/", views.email_detail, name="email_detail"),
    path("emails/<int:pk>/save/", views.email_save, name="email_save"),
    path("emails/<int:pk>/delete/", views.email_delete, name="email_delete"),
    path("emails/<int:pk>/ai/", views.email_ai_action, name="email_ai_action"),
]
