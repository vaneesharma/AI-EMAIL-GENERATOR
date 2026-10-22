import json
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .forms import EmailEditForm, EmailFilterForm, GenerateEmailForm, RegisterForm
from .models import CUSTOM_PURPOSE, PURPOSES, GeneratedEmail

DB_ERROR_MESSAGE = "Something went wrong while accessing the database. Please try again."
PAGE_SIZE = 10


# ------------------------------------------------------------------ helpers
def day_range(day):
    """Start (inclusive) and end (exclusive) of a calendar day, timezone-aware.

    Range filters are used instead of `created_at__date` because the __date
    lookup needs MySQL time-zone tables, which are missing on many installs.
    """
    start = timezone.make_aware(datetime.combine(day, time.min))
    return start, start + timedelta(days=1)


def user_emails(user):
    """Every query on emails goes through here so users only see their own."""
    return GeneratedEmail.objects.filter(user=user)


def email_inputs(email):
    """The original form inputs of a saved email, as keyword arguments for the AI."""
    return {
        "purpose": email.purpose,
        "recipient_type": email.recipient_type,
        "tone": email.tone,
        "language": email.language,
        "important_points": email.important_points,
        "additional_instructions": email.additional_instructions,
    }


# ------------------------------------------------------------------ auth
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except DatabaseError:
            messages.error(request, DB_ERROR_MESSAGE)
        else:
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect("dashboard")
    return render(request, "register.html", {"form": form})


# ------------------------------------------------------------------ dashboard
@login_required
def dashboard(request):
    context = {"total": 0, "today": 0, "recent": []}
    try:
        emails = user_emails(request.user)
        today_start, today_end = day_range(timezone.localdate())
        context["total"] = emails.count()
        context["today"] = emails.filter(created_at__gte=today_start, created_at__lt=today_end).count()
        context["recent"] = list(emails[:5])
    except DatabaseError:
        messages.error(request, DB_ERROR_MESSAGE)
    return render(request, "dashboard.html", context)


# ------------------------------------------------------------------ generate
@login_required
def generate_email(request):
    if request.method == "POST":
        form = GenerateEmailForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                subject, body = services.generate_email(
                    purpose=data["final_purpose"],
                    recipient_type=data["recipient_type"],
                    tone=data["tone"],
                    language=data["language"],
                    important_points=data["important_points"],
                    additional_instructions=data["additional_instructions"],
                )
            except services.AIServiceError as exc:
                messages.error(request, str(exc))
                return render(request, "generate_email.html", {"form": form})

            try:
                email = GeneratedEmail.objects.create(
                    user=request.user,
                    purpose=data["final_purpose"],
                    recipient_type=data["recipient_type"],
                    tone=data["tone"],
                    language=data["language"],
                    important_points=data["important_points"],
                    additional_instructions=data["additional_instructions"],
                    subject=subject,
                    body=body,
                )
            except DatabaseError:
                messages.error(request, DB_ERROR_MESSAGE)
                return render(request, "generate_email.html", {"form": form})

            messages.success(request, "Your email has been generated and saved to your history.")
            return redirect("email_result", pk=email.pk)
        messages.error(request, "Please correct the errors below.")
    else:
        form = GenerateEmailForm(initial=reuse_initial(request))
    return render(request, "generate_email.html", {"form": form})


def reuse_initial(request):
    """Pre-fill the form from an old email when the user clicks 'Reuse'."""
    reuse_id = request.GET.get("reuse", "")
    if not reuse_id.isdigit():
        return {}
    email = user_emails(request.user).filter(pk=int(reuse_id)).first()
    if email is None:
        return {}
    initial = email_inputs(email)
    initial.pop("purpose")
    if email.purpose in PURPOSES:
        initial["purpose"] = email.purpose
    else:
        initial["purpose"] = CUSTOM_PURPOSE
        initial["custom_purpose"] = email.purpose
    return initial


# ------------------------------------------------------------------ view / edit
def render_editor(request, template, email, form=None):
    form = form or EmailEditForm(instance=email)
    return render(request, template, {"email": email, "form": form})


@login_required
def email_result(request, pk):
    email = get_object_or_404(user_emails(request.user), pk=pk)
    return render_editor(request, "email_result.html", email)


@login_required
def email_detail(request, pk):
    email = get_object_or_404(user_emails(request.user), pk=pk)
    return render_editor(request, "email_detail.html", email)


@login_required
@require_POST
def email_save(request, pk):
    email = get_object_or_404(user_emails(request.user), pk=pk)
    form = EmailEditForm(request.POST, instance=email)
    if form.is_valid():
        try:
            form.save()
        except DatabaseError:
            messages.error(request, DB_ERROR_MESSAGE)
        else:
            messages.success(request, "Email saved successfully.")
            return redirect("email_detail", pk=email.pk)
    else:
        messages.error(request, "Subject and email body cannot be empty.")
    return render_editor(request, "email_detail.html", email, form)


@login_required
@require_POST
def email_delete(request, pk):
    email = get_object_or_404(user_emails(request.user), pk=pk)
    try:
        email.delete()
    except DatabaseError:
        messages.error(request, DB_ERROR_MESSAGE)
        return redirect("email_detail", pk=pk)
    messages.success(request, "Email deleted.")
    return redirect("email_history")


# ------------------------------------------------------------------ AI actions (AJAX)
@login_required
@require_POST
def email_ai_action(request, pk):
    """Improve / shorter / formal / friendly / regenerate. Returns JSON.

    The new text is only sent back to the editor; the user presses Save to keep it.
    """
    email = get_object_or_404(user_emails(request.user), pk=pk)
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    action = payload.get("action")
    try:
        if action == "regenerate":
            subject, body = services.generate_email(**email_inputs(email), variation=True)
        elif action in services.MODIFY_INSTRUCTIONS:
            subject = str(payload.get("subject", "")).strip()
            body = str(payload.get("body", "")).strip()
            if not subject or not body:
                return JsonResponse({"error": "Subject and email body cannot be empty."}, status=400)
            if len(body) > 10000:
                return JsonResponse({"error": "The email is too long to process."}, status=400)
            subject, body = services.modify_email(subject, body, action, language=email.language)
        else:
            return JsonResponse({"error": "Unknown action."}, status=400)
    except services.AIServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({"subject": subject, "body": body})


# ------------------------------------------------------------------ history
@login_required
def email_history(request):
    filter_form = EmailFilterForm(request.GET or None, user=request.user)
    emails = user_emails(request.user)

    if filter_form.is_valid():
        data = filter_form.cleaned_data
        if data["q"]:
            emails = emails.filter(Q(subject__icontains=data["q"]) | Q(purpose__icontains=data["q"]))
        if data["purpose"]:
            emails = emails.filter(purpose=data["purpose"])
        if data["tone"]:
            emails = emails.filter(tone=data["tone"])
        if data["date"]:
            start, end = day_range(data["date"])
            emails = emails.filter(created_at__gte=start, created_at__lt=end)

    query = request.GET.copy()
    query.pop("page", None)

    try:
        page = Paginator(emails, PAGE_SIZE).get_page(request.GET.get("page"))
        list(page)  # force the query now so a database error is caught here
    except DatabaseError:
        messages.error(request, DB_ERROR_MESSAGE)
        page = Paginator([], PAGE_SIZE).get_page(1)

    context = {
        "page": page,
        "filter_form": filter_form,
        "querystring": query.urlencode(),
        "filters_active": bool(query),
    }
    return render(request, "email_history.html", context)
